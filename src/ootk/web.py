"""FastAPI web GUI: `uvicorn ootk.web:app`."""
import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import os
import re
import secrets
from collections import Counter
import shlex
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
import psycopg
from psycopg.rows import dict_row
from starlette.exceptions import HTTPException as StarletteHTTPException

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import WITHHELD_MAX, derive_primary_element, withheld_summary
from ootk.assets import CachedStaticFiles, CompressionMiddleware, static_url
from ootk.db import (
    DB_CONFIG, DEFAULT_MAPPING, DatabaseOutdated, MAPPING_SYSTEMS, approved_testimonials, delete_testimonial, fetch_all_cards, fetch_cards_correspondences,
    list_testimonials, load_report_by_link, load_report_settings, save_spread_session, save_testimonial,
    session_has_testimonial, set_testimonial_approved,
)
from ootk.lockout import FailedLogins
from ootk.report import MAPPING_LABELS, analyze_reading
from ootk.rules import element_dignity
from ootk import atlas
from ootk import significator as significator_methods
from ootk.shuffle import (
    draw_spread, duplicate_in_operation, has_significator_position, operation_number, resolve_significator,
)
from ootk.spreads import SPREADS, spread_positions, spread_segments
from ootk.visual import ASPECT_TYPES, ELEMENT_COLORS, art_note, build_report_view, card_image_url, card_srcset, short_card_name, withheld_view

VALID_MAPPINGS = set(MAPPING_SYSTEMS)
VALID_FRAMEWORKS = {"auto", "light_descent", "soul_formation", "life_path", "post_mortem"}
VALID_DRAW_MODES = {"seed", "manual"}
VALID_OUTPUT_FORMATS = {"visual", "markdown"}
TOPIC_MAX = 2000
SHARED_SEED_MAX = 64
# Every other field is a short name (a spread key, a system, a card title); the card list is at
# most a whole deck of titles.
FIELD_MAX = 64
SELECTED_CARDS_MAX = 4000
# Report links: secrets.token_urlsafe(16) (22 characters) or, for readings from before random
# links, a 32-character hex UUID. Anything else can't be a link and never reaches the database.
REPORT_LINK = re.compile(r"[A-Za-z0-9_-]{16,64}")
# Readings saved before 'thoth' existed stored 'golden_dawn' for what is now 'thoth' (the
# swap was always applied). New readings carry this version, so old links keep their cards.
MAPPING_VERSION = 2
# Readings saved before draw version 2 dealt every operation of the Opening of the Key from one
# shuffle; now each operation reshuffles (shuffle.operation_seed). Their saved cards still show,
# but their seed would draw other cards, so their report offers no share link or command.
DRAW_VERSION = 2
# When the reshuffle went live (PR #61 merged). Readings saved after it but before readings
# recorded their draw version already draw under it.
RESHUFFLE_SINCE = datetime(2026, 10, 5, 3, 25, 44, tzinfo=timezone.utc)

# A full Opening of the Key report needs about 10 MB while it is built, rendered and
# compressed, so 40 at once (the thread pool's size) could pass the 512 MB of a small host, and
# the memory isn't handed back afterwards. Python runs one render at a time anyway (the GIL), so
# at most WEB_THREADS readings are handled at once and the rest wait their turn, outside the
# thread pool. The pool itself keeps its default size: static files are read in it too, and a
# reading that waits on a slow database must not hold up the site's CSS, images and other pages.
WEB_THREADS = int(os.getenv("WEB_THREADS", "8"))
reading_slots = asyncio.Semaphore(WEB_THREADS)


def builds_a_reading(path: str) -> bool:
    """Paths that analyse and render a whole reading: drawing one, a share link, a saved
    report, and their JSON downloads."""
    return path == "/generate_report" or path.startswith(("/reading", "/report/"))


# No interactive API docs: the site has no API clients, and the docs page loads scripts from a CDN.
app = FastAPI(title="OOTK Thoth Graphic GUI", docs_url=None, redoc_url=None, openapi_url=None)
log = logging.getLogger("ootk.web")


static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", CachedStaticFiles(directory=str(static_dir)), name="static")
app.add_middleware(CompressionMiddleware)


class ReadingSlots:
    """One of the WEB_THREADS reading slots per reading page, held until the page (built,
    rendered and compressed) has been handed on."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not builds_a_reading(scope["path"]):
            await self.app(scope, receive, send)
            return
        async with reading_slots:
            await self.app(scope, receive, send)


app.add_middleware(ReadingSlots)


# Form posts are a few kilobytes at most (the question is capped at TOPIC_MAX characters), so
# anything far larger is refused before it is read, rather than parsed into memory.
MAX_BODY_BYTES = 64 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        if length is None or not length.isdigit() or int(length) > MAX_BODY_BYTES:
            return error_page(request, 413, "This form is too large",
                              "The settings sent were far larger than any reading needs. "
                              "Go back, shorten the question and try again.")
    return await call_next(request)


failed_logins = FailedLogins()


def visitor_address(request: Request) -> str:
    """Who is knocking, for the password lockout. On Render every request comes through
    Cloudflare, which sets CF-Connecting-IP to the real visitor and overwrites any copy the
    visitor sends; X-Forwarded-For starts with whatever the visitor wrote, so it can't be used."""
    if os.getenv("RENDER"):
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("true-client-ip")
        if forwarded:
            return forwarded.strip()[:64]
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def require_password(request: Request, call_next):
    """When APP_PASSWORD is set (e.g. on a public host), every page asks for it via HTTP
    Basic auth; any user name is accepted. Unset, the app is open as before.

    Ten wrong passwords from one visitor within 15 minutes lock that visitor out for 15
    minutes; while locked out, even the right password is refused, so guessing gains nothing."""
    password = os.getenv("APP_PASSWORD")
    if not password:
        return await call_next(request)
    visitor = visitor_address(request)
    wait = failed_logins.retry_after(visitor)
    if wait:
        return locked_out(wait)
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "basic":
        try:
            given = base64.b64decode(encoded).decode("utf-8").partition(":")[2]
        except (ValueError, UnicodeDecodeError):
            given = ""
        if secrets.compare_digest(given.encode(), password.encode()):
            failed_logins.succeeded(visitor)
            return await call_next(request)
        # Only a password that was actually sent counts; the browser's first, empty request doesn't.
        wait = failed_logins.failed(visitor)
        if wait:
            log.warning("password lockout started for one visitor (%d wrong passwords)",
                        failed_logins.attempts)
            return locked_out(wait)
    return PlainTextResponse("Password required.", status_code=401,
                             headers={"WWW-Authenticate": 'Basic realm="ootk"'})


def locked_out(wait: int):
    minutes = max(1, (wait + 59) // 60)
    return PlainTextResponse(f"Too many wrong passwords. Try again in {minutes} minute"
                             f"{'' if minutes == 1 else 's'}.", status_code=429,
                             headers={"Retry-After": str(wait)})


# Pages use inline <script> and style attributes, so scripts and styles allow 'unsafe-inline';
# everything else (images, fonts, fetches, forms, framing) is limited to this site.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # Links out (e.g. to an LLM) carry only the site's origin, never a /report/<link> address.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Browser hardening headers on every response, including the password prompt. HSTS only
    over https (on Render, uvicorn's --proxy-headers sets the scheme from X-Forwarded-Proto)."""
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if is_private_path(request.url.path):
        # A saved reading carries the querent's question: no copies in shared caches or the
        # browser's back-forward store, and never in search results.
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


class HeadAsGet:
    """Answers HEAD like GET, without the body. FastAPI routes declared with @app.get refuse
    HEAD with 405, so uptime monitors and link checkers that use HEAD saw every page as down.
    Added last, so it wraps everything else: HEAD gets the same password check and headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "HEAD":
            return await self.app(scope, receive, send)
        sent_body = False

        async def send_headers_only(message):
            nonlocal sent_body
            if message["type"] != "http.response.body":
                return await send(message)
            if not sent_body:
                sent_body = True
                await send({"type": "http.response.body", "body": b"", "more_body": False})

        await self.app(dict(scope, method="GET"), receive, send_headers_only)


app.add_middleware(HeadAsGet)


def is_private_path(path: str) -> bool:
    return (path.startswith(("/report/", "/admin")) or path in ("/generate_report", "/testimonial"))


class RedactReportLinks(logging.Filter):
    """Access logs show /report/<redacted>: a report link opens a saved reading and its
    question, so it shouldn't sit in the host's logs where anyone with log access can read it."""

    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) >= 3 and isinstance(record.args[2], str):
            args = list(record.args)
            args[2] = REPORT_LINK_IN_PATH.sub("/report/<redacted>", args[2])
            record.args = tuple(args)
        return True


REPORT_LINK_IN_PATH = re.compile(r"/report/[^/?#\s]+")
logging.getLogger("uvicorn.access").addFilter(RedactReportLinks())

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

REPO_URL = "https://github.com/hampshirecottage-ai/ootk-thoth-engine"
BUG_REPORT_URL = f"{REPO_URL}/issues/new?template=bug_report.yml"
CONTACT_URL = f"{REPO_URL}/discussions"
SITE_DESCRIPTION = ("Draw a Thoth tarot spread and get its Golden Dawn dignities, decans and "
                    "Liber 777 correspondences calculated, as a prompt for your LLM to interpret.")
# The spreads from first steps to the full Opening of the Key: (level, name, spread keys, what
# it teaches). Start here lists them and the spread picker groups its options the same way.
SPREAD_STAGES = [
    ("Stage 1", "Single cards", ["1", "3"],
     "What one card carries: its attribution, element, Hebrew letter or Sephira, and King Scale "
     "colour. Three cards add a past, present and future."),
    ("Stage 2", "Elements in pairs", ["2", "4", "5"],
     "Elemental dignities: whether neighbouring cards strengthen or weaken each other, and the "
     "four worlds of the Tetragrammaton."),
    ("Stage 3", "Whole layouts", ["6", "7"],
     "Cards placed on the planets of the hexagram and the Sephiroth of the Tree of Life, and how "
     "each position relates to the others."),
    ("Stage 4", "The Opening of the Key", ["8", "9", "10", "11", "12"],
     "The Golden Dawn&rsquo;s long method, one operation at a time: a significator, then the "
     "houses, the signs and the 36 decans, and finally all four together."),
]
# The spread a first visit starts on: three cards, like Start here step 3.
DEFAULT_SPREAD = "3"
# Pages search engines may list (the sitemap adds today's card). Saved and shared readings stay out.
PUBLIC_PAGES = ["/", "/pick", "/start", "/history", "/examples", "/library", "/maps", "/method"]


def site_url(request: Request) -> str:
    """The public address, for links that must be absolute (link previews, sitemap).

    SITE_URL wins, then the address Render gives the service, then the address the request
    came in on (fine locally; behind a proxy it may say http instead of https)."""
    url = os.getenv("SITE_URL") or os.getenv("RENDER_EXTERNAL_URL") or str(request.base_url)
    return url.rstrip("/")


def wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def error_page(request: Request, status: int, heading: str, message: str, retry: bool = False,
               headers: dict | None = None):
    """A readable error page for browsers, with a way back (and a retry when the fault is
    passing); API clients get the same message as JSON."""
    if not wants_html(request):
        return JSONResponse({"detail": message}, status_code=status, headers=headers)
    retry_link = ('<a href="" onclick="location.reload(); return false;">Try again</a> '
                  if retry else '')
    return HTMLResponse(status_code=status, headers=headers, content=(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex">'
        f'<title>{html.escape(heading)}</title><style>'
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
        'background:#2e8a56;color:#ffe0a0;margin:0;padding:24px}'
        'main{max-width:560px;margin:10vh auto}h1{font-size:1.3em}'
        'a{display:inline-block;background:#0d2617;color:#fff;padding:10px 16px;margin:0 6px 6px 0;'
        'border-radius:6px;text-decoration:none;font-weight:600}'
        '@media (prefers-color-scheme:dark){body{background:#121212;color:#e0e0e0}a{background:#2e8a56}}'
        '.more{font-size:.9em}.more a.plain{background:none;color:inherit;padding:0;'
        'text-decoration:underline;font-weight:normal}</style></head><body><main>'
        f'<h1>{html.escape(heading)}</h1><p>{html.escape(message)}</p><p>{retry_link}'
        '<a href="/" onclick="if (history.length > 1) { history.back(); return false; }">'
        '&larr; Back to settings</a></p>'
        f'<p class="more">Think this is a mistake? <a class="plain" href="{BUG_REPORT_URL}" '
        'target="_blank" rel="noopener">Report a bug</a></p></main></body></html>'))


# Headings for errors the router raises itself (an unknown address, a wrong method).
ROUTER_ERRORS = {404: ("Page not found", "There is no page at this address."),
                 405: ("This page can’t be used that way",
                       "This address doesn’t accept that kind of request.")}


@app.exception_handler(StarletteHTTPException)
async def form_error_page(request: Request, exc: StarletteHTTPException):
    """A browser gets a readable page with a way back; API clients keep JSON."""
    if not wants_html(request):
        return await http_exception_handler(request, exc)
    if not isinstance(exc, HTTPException) and exc.status_code in ROUTER_ERRORS:
        heading, message = ROUTER_ERRORS[exc.status_code]
        return error_page(request, exc.status_code, heading, message)
    return error_page(request, exc.status_code, "This reading can’t be shown", str(exc.detail),
                      headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def incomplete_form_page(request: Request, exc: RequestValidationError):
    """A form or link missing a required field: a page saying which, not a JSON 422."""
    if not wants_html(request):
        return await request_validation_exception_handler(request, exc)
    fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
    message = ("The form arrived incomplete" + (f" (missing or invalid: {', '.join(fields)})" if fields else "")
               + ". Go back, check the settings and try again.")
    return error_page(request, 400, "This reading can’t be shown", message)


@app.exception_handler(psycopg.OperationalError)
async def database_unreachable_page(request: Request, exc: psycopg.OperationalError):
    """The database is down, asleep, out of connections or too slow: say so and offer a retry.
    Pages that need no cards (Start here, Library, Method) keep working meanwhile."""
    log.warning("database unreachable on %s: %s", request.url.path, exc)
    return error_page(request, 503, "The card database isn’t answering",
                      "The site is up, but it couldn’t reach its card database just now. This "
                      "usually clears within a minute, so please try again. Start here, the Library "
                      "and the Method pages work without it.", retry=True, headers={"Retry-After": "30"})


@app.exception_handler(DatabaseOutdated)
async def database_outdated_page(request: Request, exc: DatabaseOutdated):
    log.error("database needs a migration: %s", exc)
    return error_page(request, 503, "The card database needs an update",
                      "The card tables are older than this version of the site, so readings can’t "
                      "be built until the site owner runs the latest database migration.")


@app.exception_handler(Exception)
async def unexpected_error_page(request: Request, exc: Exception):
    """Anything else: a plain apology instead of 'Internal Server Error'. The traceback still
    reaches the server log (Starlette re-raises after this handler)."""
    return error_page(request, 500, "Something went wrong on our side",
                      "The page couldn’t be built because of an error in the site. Trying again "
                      "may work; if it keeps happening, please report it.", retry=True)


templates.env.globals.update(static_url=static_url, card_image_url=card_image_url, art_note=art_note, element_colors=ELEMENT_COLORS,
                             card_srcset=card_srcset, bug_report_url=BUG_REPORT_URL,
                             contact_url=CONTACT_URL, repo_url=REPO_URL, site_url=site_url,
                             site_description=SITE_DESCRIPTION, spread_stages=SPREAD_STAGES,
                             default_spread=DEFAULT_SPREAD)


def get_db_connection():
    """A connection, tried twice: a hosted database that sleeps when idle (Neon) can refuse the
    first attempt while it wakes. A second failure reaches database_unreachable_page."""
    started = time.monotonic()
    try:
        return psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    except psycopg.OperationalError as e:
        # A refusal comes back at once; a timeout has already used up the wait, so no retry.
        if time.monotonic() - started > 3:
            raise
        log.warning("database connection failed, retrying once: %s", e)
        time.sleep(1)
        return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


# thoth_cards and correspondences are reference data that change only with a migration, so the
# pages read them once per process, like the sample and the sign carriers. Drawing and analysing
# a reading then needs no database round trip; only saving and opening a saved report connect.
# After running a migration, restart the app to pick it up.
_reference_cache = {}


def reference_deck():
    """fetch_all_cards, read once per process. An empty table isn't kept, so a database
    loaded after start-up is picked up on the next request."""
    if "deck" not in _reference_cache:
        with get_db_connection() as conn:
            deck = fetch_all_cards(conn)
        if not deck:
            return deck
        _reference_cache["deck"] = deck
    return _reference_cache["deck"]


def reference_rows(system):
    """Every card's fetch_cards_correspondences row under `system`, read once per process.
    The rows are shared: callers that hand rows on copy them (card_rows)."""
    if system not in _reference_cache:
        titles = [c["title"] for c in reference_deck()]
        if not titles:
            return {}
        with get_db_connection() as conn:
            _reference_cache[system] = fetch_cards_correspondences(conn, titles, system=system)
    return _reference_cache[system]


def card_rows(titles, system):
    """{title: row} for the drawn `titles` under `system`; titles not in the deck are absent."""
    rows = reference_rows(system)
    return {t: dict(rows[t]) for t in titles if t in rows}


def withheld_cards(deck, drawn_titles, system):
    """db.load_withheld from the cached rows: analysis.withheld_summary, or None."""
    if len(deck) - len(set(drawn_titles)) > WITHHELD_MAX:
        return None
    rows = reference_rows(system)
    return withheld_summary([rows[c["title"]] for c in deck if c["title"] in rows], drawn_titles)


def quoted(value: str) -> str:
    """A visitor's value repeated in an error message, cut short so a page can't be made to
    echo back an arbitrarily long text."""
    return repr(value if len(value) <= 40 else value[:40] + "…")


def check_lengths(**fields):
    """400 for any field longer than FIELD_MAX; names it without repeating its value."""
    for name, value in fields.items():
        if len(value) > FIELD_MAX:
            raise HTTPException(status_code=400, detail=f"The {name.replace('_', ' ')} field is too long "
                                                        f"(at most {FIELD_MAX} characters).")


def refuse_nul(**fields):
    """400 for a NUL character, which PostgreSQL can't store in text: without this check the
    reading or testimonial would fail to save. Only a hand-made request can send one."""
    for name, value in fields.items():
        if "\x00" in value:
            raise HTTPException(status_code=400, detail=f"The {name.replace('_', ' ')} field contains "
                                                        f"a character that can't be saved.")


def new_seed() -> str:
    """A fresh six-digit seed, shown on the report so the reading can be repeated."""
    return str(secrets.randbelow(900000) + 100000)


def cli_command(spread_key, seed, mapping_system, framework, significator, topic) -> str:
    """The `ootk` command that repeats a seeded reading from the terminal."""
    parts = ["ootk", "--spread", spread_key, "--seed", seed, "--mapping", mapping_system,
             "--framework", framework]
    if significator:
        parts += ["--significator", significator]
    if topic:
        parts += ["--topic", topic]
    return " ".join(shlex.quote(p) for p in parts)


def reading_export(spread_name, settings, significator, framework, framework_basis,
                   element_counts, spread_results, view, dignity_matrix, spatial_matrix,
                   withheld=None):
    """The whole reading as plain JSON data, for the report's JSON download."""
    reading = {
        "spread": spread_name,
        "settings": {k: v for k, v in settings.items() if k not in ("output_format", "selected_cards")},
        "significator": significator,
        "framework": framework,
        "framework_basis": framework_basis,
        "element_counts": element_counts,
        "cards": [
            dict(item["card_data"], position_number=item["position_number"],
                 position_name=item["position_name"], primary_element=card["element"],
                 dignified=card["dignified"])
            for item, card in zip(spread_results, view["card_details"])
        ],
        "dignities": dignity_matrix,
        "aspects": spatial_matrix,
        "withheld": [row["title"] for row in withheld["cards"]] if withheld else [],
    }
    # Round-trip through json so dates, decimals and the like become plain strings.
    return json.loads(json.dumps(reading, default=str))


# The start page shows this reading before asking for any settings: the full Opening of the
# Key, so a visitor sees every operation at once. The seed is a throwaway number and the
# significator a fixed card, so the sample holds no personal data, and the same seed always
# draws the same cards.
SAMPLE_SETTINGS = {
    "spread_key": "12", "seed": "12345", "topic": "", "significator": "Queen of Cups",
    "framework": "auto", "mapping_system": DEFAULT_MAPPING, "draw_mode": "seed",
    "output_format": "visual",
}
_sample_cache = {}

NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
OP_SHORT_NAMES = {"8": "The heap", "9": "Twelve houses", "10": "Twelve signs", "11": "Thirty-six decans"}
OP_UNITS = {"8": "in the heap", "9": "houses", "10": "signs", "11": "decans"}
DIGNITY_KINDS = ((2, "same", ("shares an element", "share an element")),
                 (1, "friendly", ("is friendly", "are friendly")),
                 (-2, "contrary", ("is contrary", "are contrary")),
                 (0, "neutral", ("is neutral", "are neutral")))


def _and_list(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _count(n):
    return NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)


def _the(data):
    """'the Queen of Cups', 'The Hierophant', 'Art': how a card reads mid-sentence."""
    name = short_card_name(data["title"])
    return name if name.startswith("The ") or data.get("arcana_type") == "Major" else f"the {name}"


def _position_name(item):
    """'[Op 1] 2. Development of Question (Left Pair A)' -> 'Development of Question (Left Pair A)'."""
    return re.sub(r"^(\[Op \d+\]\s*)?\d+\.\s*", "", item["position_name"])


def _dignity_totals(pairs):
    totals = {key: sum(1 for d in pairs if d["score"] == score) for score, key, _ in DIGNITY_KINDS}
    totals["net"] = sum(d["score"] for d in pairs)
    totals["pairs"] = len(pairs)
    return totals


def _aspect_totals(pairs):
    counts = Counter(p.get("aspect_name") or "Unaspected" for p in pairs)
    return {"strong": sum(1 for p in pairs if abs(p.get("score_modifier") or 0) >= 2),
            "by_type": [(a, counts[a]) for a in ASPECT_TYPES if counts[a]]}


def _sample_card(item, start):
    d = item["card_data"]
    idx = item["position_number"] - 1
    return {
        "n": idx - start + 1, "position": _position_name(item), "title": d["title"],
        "short": short_card_name(d["title"]), "element": derive_primary_element(d),
        "attribution": d.get("attribution") or "", "letter": d.get("hebrew_letter") or "",
        "place": d.get("spatial_dimension") or "", "place_type": d.get("spatial_type") or "",
        "img": card_image_url(d["title"], "small"), "art": art_note(d["title"]),
        "dignities": [],   # filled in by sample_view, which has the whole operation
    }


def sample_summary(r, settings):
    """Two plain-language paragraphs on what the sample drew and what was calculated.
    Facts only: the site gives the AI the instructions and never interprets the cards."""
    items = r["spread_results"]
    segments = spread_segments(items, settings["spread_key"])
    heap = items[segments[0][1]:segments[0][2]]
    sizes = _and_list(f"{e - s} {OP_UNITS.get(k, 'cards')}"
                      for k, s, e, _ in segments) if len(segments) > 1 else None
    first = f"Seed {settings['seed']}"
    if settings["significator"]:
        first += f", with {_the(heap[0]['card_data'])} as significator,"
    first += f" dealt {len(items)} cards"
    first += f" over {_count(len(segments))} operations: {sizes}." if sizes else "."
    if len(heap) > 2:
        last = heap[-1]
        first += (f" The heap opens on {_the(heap[0]['card_data'])} ({_position_name(heap[0]).lower()})"
                  f" and closes on {_the(last['card_data'])} ({_position_name(last).lower()}).")

    counts = [(e, c) for e, c in r["element_counts"].items() if c]
    second = [f"Across all {len(items)} cards the elements are "
              f"{_and_list(f'{c} {e}' for e, c in counts)}."]
    dig = _dignity_totals(r["dignity_matrix"])
    if dig["pairs"]:
        parts = [f"{dig[key]} {phrases[dig[key] != 1]}" for _, key, phrases in DIGNITY_KINDS if dig[key]]
        second.append(f"Of the {dig['pairs']} scored pairs, {_and_list(parts)}, a net score of {dig['net']:+d}.")
    on_cube = [i for i in heap if i["card_data"].get("spatial_dimension")]
    if on_cube:
        verb = "sits" if len(on_cube) == 1 else "sit"
        second.append(f"{_count(len(on_cube)).capitalize()} of the heap's cards {verb} on the Cube of Space.")
    second.append("What it means is left to your AI.")
    return [first, " ".join(second)]


def sample_view(r, settings):
    """Everything the start page shows of the sample: the summary, the heap and wheel for the
    diagram, the element breakdown, the cube positions and one summary per operation."""
    items = r["spread_results"]
    segments = spread_segments(items, settings["spread_key"])
    ops = []
    for key, start, end, name in segments:
        dignities = [d for d in r["dignity_matrix"] if start <= d["from_index"] < end]
        cards = []
        for item in items[start:end]:
            idx = item["position_number"] - 1
            card = _sample_card(item, start)
            card["dignities"] = [
                {"with": short_card_name(items[d["to_index"] if d["from_index"] == idx else d["from_index"]]
                                         ["card_data"]["title"]), "score": d["score"]}
                for d in dignities if idx in (d["from_index"], d["to_index"])]
            cards.append(card)
        ops.append({
            "key": key, "name": OP_SHORT_NAMES.get(key, SPREADS[key]["name"]),
            "full_name": name or SPREADS[key]["name"], "cards": cards,
            "dignity": _dignity_totals(dignities),
            "aspects": _aspect_totals([p for p in r["spatial_matrix"] if start <= p["from_index"] < end]),
        })
    total = len(items)
    top = max(r["element_counts"].values()) or 1      # bars are scaled to the largest count
    elements = [{"name": e, "count": n, "pct": round(100 * n / top)}
                for e, n in r["element_counts"].items() if e != "Spirit" or n]
    by_key = {op["key"]: op for op in ops}
    heap = by_key.get("8", ops[0])["cards"]
    wheel = by_key["10"]["cards"] if "10" in by_key else []
    return {
        "seed": settings["seed"], "significator": settings["significator"],
        "spread_name": r["spread_name"], "card_count": total,
        "summary": sample_summary(r, settings), "elements": elements, "ops": ops,
        "heap": heap, "wheel": wheel,
        "cube": [c for c in heap if c["place"]],
        "prompt": r["analytical_prompt"], "url": share_path(settings),
    }


def sample_reading(deck):
    """The start page's sample: drawn and analysed once per process, then reused. None when
    the deck can't produce it (an empty or partial database), so the page still renders."""
    if "sample" in _sample_cache:
        return _sample_cache["sample"]
    if len(deck) != 78:            # another deck size would draw other cards for this seed
        return None
    try:
        card_titles, significator_label = seeded_draw(deck, SAMPLE_SETTINGS["seed"],
                                                      SAMPLE_SETTINGS["spread_key"],
                                                      SAMPLE_SETTINGS["significator"])
        r = run_reading(SAMPLE_SETTINGS, card_titles, significator_label, deck)
    except (HTTPException, LookupError, ValueError):
        return None
    sample = sample_view(r, SAMPLE_SETTINGS)
    _sample_cache["sample"] = sample
    return sample


def seeded_draw(deck, seed, spread_key, significator):
    """The cards `seed` draws for the spread, exactly as `ootk --seed` does.
    Returns (card_titles, significator_label)."""
    positions = spread_positions(spread_key)
    sig_card = resolve_significator(deck, significator)
    if significator and sig_card is None:
        raise HTTPException(status_code=400,
                            detail=f"Significator {quoted(significator)} was not found in the deck. "
                                   f"Pick a title from the list, e.g. 'Queen of Cups' "
                                   f"or 'Princess of Disks'.")
    if sig_card is None and has_significator_position(positions):
        raise HTTPException(status_code=400,
                            detail=f"{SPREADS[spread_key]['name']} needs a significator. "
                                   f"Choose one under Significator on the start page.")
    try:
        card_titles, pinned = draw_spread(deck, seed, positions, sig_card)
    except ValueError as e:                 # a card table that is empty or only partly loaded
        log.warning("cannot draw: %s", e)
        raise HTTPException(status_code=503, detail="The card database is incomplete, so no cards "
                                                    "can be drawn. Please try again later.") from e
    return card_titles, (sig_card["title"] if pinned else "None (spread has no significator position)")


def reshuffles(spread_key) -> bool:
    """True for a spread dealt over several operations, each from its own shuffle."""
    return len({operation_number(p) for p in spread_positions(spread_key)}) > 1


def share_path(settings) -> str:
    """The /reading address that redraws a seeded reading. It carries the seed and settings
    but never the topic, so a shared link doesn't reveal what the question was."""
    params = {"seed": settings["seed"], "spread": settings["spread_key"],
              "system": settings["mapping_system"]}
    if settings["framework"] != "auto":
        params["framework"] = settings["framework"]
    if settings["significator"]:
        params["significator"] = settings["significator"]
    return "/reading?" + urlencode(params)


def settings_page(request: Request, name: str, mode: str):
    """Sync endpoint body: FastAPI executes in threadpool to prevent blocking the event loop."""
    cards = reference_deck()
    sample = sample_reading(cards) if mode == "seed" else None
    testimonial = testimonial_of_the_day() if mode == "seed" else None
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "cards": cards,
            "mode": mode,
            "sample": sample,
            "testimonial": testimonial,
            "show_testimonials": mode == "seed",
            "spreads": SPREADS,
            "positions": {key: spread_positions(key) for key in SPREADS},
            "sig_ranks": significator_methods.RANKS,
            "sig_suits": significator_methods.SUITS,
            "birth_spans": significator_methods.BIRTH_SPANS,
        }
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request):
    """Search engines may list the start, pick and card-of-the-day pages, never saved or
    shared readings."""
    return ("User-agent: *\n"
            "Disallow: /report/\n"
            "Disallow: /generate_report\n"
            "Disallow: /reading\n"
            f"\nSitemap: {site_url(request)}/sitemap.xml\n")


@app.get("/sitemap.xml")
def sitemap_xml(request: Request):
    base = site_url(request)
    pages = PUBLIC_PAGES + [f"/day/{utc_today().isoformat()}"]
    urls = "".join(f"<url><loc>{html.escape(base + path)}</loc></url>" for path in pages)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    media_type="application/xml")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Browsers and crawlers ask for /favicon.ico whatever the page links to."""
    return FileResponse(static_dir / "site" / "favicon.ico", media_type="image/x-icon",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/", response_class=HTMLResponse)
def main_gui(request: Request):
    """Start page: a sample reading and the settings. '/?seed=...' opens that shared reading."""
    if request.query_params.get("seed"):
        return RedirectResponse(f"/reading?{request.url.query}", status_code=307)
    return settings_page(request, "index.html", "seed")


@app.get("/pick", response_class=HTMLResponse)
def pick_gui(request: Request):
    """Pick by hand: the same settings plus the spread board and card catalog."""
    return settings_page(request, "pick.html", "manual")


# ---------- guide pages: start here, examples, library, method ----------

# The examples page: throwaway seeds, smallest spread first. "shows" says what to look at in
# the report, never what the cards mean; interpreting them is the LLM's job.
EXAMPLES = [
    {"spread_key": "1", "seed": "2026-01-01", "title": "One card",
     "shows": "The smallest reading: one card with its attribution, Hebrew letter and King "
              "Scale colour. The seed is a date, which is how the card of the day works."},
    {"spread_key": "2", "seed": "777", "title": "Two cards",
     "shows": "Two forces side by side, and the one elemental dignity between them."},
    {"spread_key": "3", "seed": "12345", "title": "Three cards",
     "shows": "Each neighbouring pair is scored by Book T's friendly and contrary elements."},
    {"spread_key": "5", "seed": "1909", "title": "Four cards",
     "shows": "One card for each letter of IHVH and its world, from Atziluth (Fire) down to "
              "Assiah (Earth)."},
    {"spread_key": "7", "seed": "10", "title": "Ten cards",
     "shows": "One card on each Sephira. The report draws the cards on the Tree of Life."},
    {"spread_key": "9", "seed": "918851", "title": "Twelve cards",
     "shows": "The Second Operation of the Opening of the Key: the twelve houses drawn as a "
              "wheel. This is the reading in the README screenshot."},
]
_examples_cache = {}


def example_readings(deck):
    """EXAMPLES with their links and, when the full deck is loaded, the cards each seed draws.
    Drawn once per process, like the start page's sample."""
    if "examples" in _examples_cache:
        return _examples_cache["examples"]
    full_deck = len(deck) == 78
    examples = []
    for ex in EXAMPLES:
        settings = {"spread_key": ex["spread_key"], "seed": ex["seed"], "framework": "auto",
                    "significator": "", "mapping_system": DEFAULT_MAPPING}
        positions = spread_positions(ex["spread_key"])
        titles = draw_spread(deck, ex["seed"], positions)[0] if full_deck else []
        examples.append(dict(ex, spread_name=SPREADS[ex["spread_key"]]["name"],
                             count=len(positions), url=share_path(settings),
                             cards=[{"title": t, "name": short_card_name(t)} for t in titles]))
    if full_deck:
        _examples_cache["examples"] = examples
    return examples


LIBRARY_FILE = BASE_DIR / "src" / "ootk" / "library.json"


def load_library():
    """The resource library: a glossary and further reading, kept in library.json so a new
    entry is one edit. Read on each request, so an edit shows without a restart."""
    with open(LIBRARY_FILE, encoding="utf-8") as f:
        library = json.load(f)
    library["terms"].sort(key=lambda t: t["term"].lower())
    return library


def guide_page(request: Request, name: str, **context):
    return templates.TemplateResponse(request=request, name=name,
                                      context=dict(context, spreads=SPREADS))


@app.get("/start", response_class=HTMLResponse)
def start_here(request: Request):
    """Start here: a path for newcomers, then the spreads grouped into learning stages."""
    return guide_page(request, "start.html",
                      sizes={key: len(spread_positions(key)) for key in SPREADS})


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    """Where the decks come from, with archival photographs (static/history)."""
    return guide_page(request, "history.html")


@app.get("/examples", response_class=HTMLResponse)
def examples_page(request: Request):
    """Sample readings at fixed seeds, each opening its full report. Without the database the
    page still lists them, just without naming the cards each seed draws."""
    try:
        deck = reference_deck()
    except psycopg.OperationalError as e:
        log.warning("examples page without card names: %s", e)
        deck = []
    return guide_page(request, "examples.html", examples=example_readings(deck))


@app.get("/library", response_class=HTMLResponse)
def library_page(request: Request):
    """Glossary, every spread and further reading."""
    return guide_page(request, "library.html", library=load_library(),
                      positions={key: spread_positions(key) for key in SPREADS})


@app.get("/maps", response_class=HTMLResponse)
def maps_page(request: Request, card: str = "", system: str = DEFAULT_MAPPING):
    """Card maps: where each card sits on the Tree, the Cube of Space, the decans, the solids
    and the elemental grid, under the chosen mapping system."""
    if system not in MAPPING_SYSTEMS:
        system = DEFAULT_MAPPING
    card = card[:FIELD_MAX]
    deck = reference_deck()
    rows = reference_rows(system)
    deck_map = atlas.deck_atlas([rows[c["title"]] for c in deck if c["title"] in rows])
    names = [(c["title"], c["short"]) for c in deck_map["cards"]]
    selected = next((i for i, n in enumerate(names) if card in n), None)
    return guide_page(request, "maps.html", atlas=deck_map, system=system, systems=MAPPING_LABELS,
                      selected=selected,
                      letters=atlas.letter_rows(deck_map), signs=atlas.sign_rows(deck_map),
                      dignity=element_dignity)


@app.get("/method", response_class=HTMLResponse)
def method_page(request: Request):
    """How a reading is made, its limits, what is stored and what it is for."""
    return guide_page(request, "method.html")


@app.post("/generate_report", response_class=HTMLResponse)
def generate_report(
    request: Request,
    spread_key: str = Form(...),
    topic: str = Form(""),
    significator: str = Form(""),
    framework: str = Form("auto"),
    mapping_system: str = Form(DEFAULT_MAPPING),
    selected_cards: str = Form(""),
    draw_mode: str = Form("manual"),
    seed: str = Form(""),
    output_format: str = Form("visual"),
):
    """Builds the spread, executes geometric/vector analysis, and renders the synthesis report.

    draw_mode 'seed' draws the cards from `seed` exactly as `ootk --seed` does (a blank seed
    gets a fresh one); 'manual' uses the comma-separated `selected_cards`.
    output_format 'visual' renders the summary-first report; 'markdown' returns the
    analytical prompt as a .md download.
    """
    topic = topic.strip()
    significator = significator.strip()
    spread_key = spread_key.strip()
    framework = framework.strip()
    mapping_system = mapping_system.strip()
    draw_mode = draw_mode.strip()
    seed = seed.strip()
    output_format = output_format.strip()

    # --- Domain Input Validation ---
    check_lengths(spread_key=spread_key, significator=significator, framework=framework,
                  mapping_system=mapping_system, draw_mode=draw_mode, output_format=output_format)
    refuse_nul(topic=topic, seed=seed, significator=significator, selected_cards=selected_cards)
    if len(selected_cards) > SELECTED_CARDS_MAX:
        raise HTTPException(status_code=400, detail="The list of cards is longer than a whole deck.")
    if spread_key not in SPREADS:
        raise HTTPException(status_code=400, detail=f"Unknown spread key: {quoted(spread_key)}.")
    if mapping_system not in VALID_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown mapping system: {quoted(mapping_system)}.")
    if framework not in VALID_FRAMEWORKS:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {quoted(framework)}.")
    if draw_mode not in VALID_DRAW_MODES:
        raise HTTPException(status_code=400, detail=f"Unknown draw mode: {quoted(draw_mode)}.")
    if output_format not in VALID_OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown output format: {quoted(output_format)}.")
    if len(seed) > SHARED_SEED_MAX:
        raise HTTPException(status_code=400, detail=f"A seed can be at most {SHARED_SEED_MAX} characters.")
    if len(topic) > TOPIC_MAX:
        raise HTTPException(status_code=400, detail=f"The question can be at most {TOPIC_MAX} characters; "
                                                    f"this one has {len(topic)}.")

    selected_spread = SPREADS[spread_key]
    positions = spread_positions(spread_key)
    significator_label = significator

    deck = None
    if draw_mode == "seed":
        seed = seed or new_seed()
        deck = reference_deck()
        card_titles, significator_label = seeded_draw(deck, seed, spread_key, significator)
    else:
        seed = ""
        card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
        significator_label = (card_titles[0] if card_titles and has_significator_position(positions)
                              else "None (spread has no significator position)")
        if not card_titles:
            raise HTTPException(status_code=400, detail="No card titles were provided.")

        if len(card_titles) != len(positions):
            raise HTTPException(
                status_code=400,
                detail=f"'{selected_spread['name']}' requires {len(positions)} cards; received {len(card_titles)}."
            )

        twice = duplicate_in_operation(positions, card_titles)
        if twice:
            raise HTTPException(status_code=400, detail=f"{quoted(twice)} is drawn twice in one operation. "
                                                        f"A card can fall only once per spread or operation.")

    settings = {
        "spread_key": spread_key, "topic": topic, "significator": significator,
        "framework": framework, "mapping_system": mapping_system, "draw_mode": draw_mode,
        "seed": seed, "output_format": "visual",
        "selected_cards": ",".join(card_titles) if draw_mode == "manual" else "",
    }
    reading = run_reading(settings, card_titles, significator_label, deck)

    with get_db_connection() as conn:
        source = f"PRNG Seed: {seed}" if seed else "GUI Selection"
        # The report's address: random, so readings can't be found by counting session numbers.
        link = secrets.token_urlsafe(16)
        session_id = save_spread_session(
            conn,
            selected_spread["name"],
            topic,
            f"{source} | Mapping: {mapping_system} | Framework: {reading['macro_framework']}",
            significator_label,
            reading["spread_results"],
            reading["dignity_matrix"],
            report_settings=dict(settings, card_titles=card_titles, significator_label=significator_label,
                                 link=link, mapping_version=MAPPING_VERSION,
                                 draw_version=DRAW_VERSION),
        )
        # An older database saves the reading without its settings; then there is no link.
        linked = bool(session_id) and (load_report_settings(conn, session_id) or {}).get("link") == link

    if output_format == "markdown":
        return PlainTextResponse(
            reading["analytical_prompt"],
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="ootk_report.md"'},
        )
    if linked:
        # Post/Redirect/Get: the report gets its own link, and reloading it saves nothing.
        return RedirectResponse(f"/report/{link}", status_code=303)
    if not session_id:
        # The database refused the write (db.py printed why). Still show the reading, but say so:
        # without a link a hand-picked reading is gone once the page is left.
        log.error("reading was not saved; showing the report without a link")
    return render_report(request, session_id, settings, reading, unsaved=not session_id)


# Short names accepted in shared links, e.g. ?system=gd.
SYSTEM_ALIASES = {"gd": "golden_dawn", "fe": "french_egyptian"}


@app.get("/reading", response_class=HTMLResponse)
def shared_reading(request: Request, seed: str = "", spread: str = "",
                   system: str = DEFAULT_MAPPING, framework: str = "auto", significator: str = ""):
    """A seeded reading rebuilt from its link, e.g. /reading?seed=918851&spread=12&system=thoth.

    The same seed and settings always draw the same cards, so the link alone is the reading.
    Nothing is saved, and no saved reading can be reached this way: those keep their random
    /report/<link> addresses.
    """
    settings, reading = shared_reading_parts(seed, spread, system, framework, significator)
    return render_report(request, None, settings, reading, shared=True,
                         json_url="/reading/json?" + request.url.query)


@app.get("/reading/json")
def shared_reading_json(seed: str = "", spread: str = "", system: str = DEFAULT_MAPPING,
                        framework: str = "auto", significator: str = ""):
    """The report's JSON download for a shared reading: the same link, drawn again."""
    settings, reading = shared_reading_parts(seed, spread, system, framework, significator)
    return reading_json_response(settings, reading)


def shared_reading_parts(seed, spread, system, framework, significator):
    """The settings and run_reading() result for a shared link's parameters."""
    seed, spread, framework, significator = seed.strip(), spread.strip(), framework.strip(), significator.strip()
    system = SYSTEM_ALIASES.get(system.strip().lower(), system.strip().lower())
    check_lengths(spread=spread, system=system, framework=framework, significator=significator)
    if not seed:
        raise HTTPException(status_code=400, detail="This link has no seed, so there are no cards to draw.")
    if len(seed) > SHARED_SEED_MAX:
        raise HTTPException(status_code=400, detail=f"A seed can be at most {SHARED_SEED_MAX} characters.")
    if spread not in SPREADS:
        raise HTTPException(status_code=400, detail=f"Unknown spread: {quoted(spread)}. Use a number from 1 to {len(SPREADS)}.")
    if system not in VALID_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown system: {quoted(system)}. Use thoth, gd or french_egyptian.")
    if framework not in VALID_FRAMEWORKS:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {quoted(framework)}.")
    settings = {
        "spread_key": spread, "topic": "", "significator": significator, "framework": framework,
        "mapping_system": system, "draw_mode": "seed", "seed": seed, "output_format": "visual",
        "selected_cards": "",
    }
    deck = reference_deck()
    card_titles, significator_label = seeded_draw(deck, seed, spread, significator)
    return settings, run_reading(settings, card_titles, significator_label, deck)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


@app.get("/today")
def card_of_the_day_today():
    """Today's card (UTC). Redirects so each day keeps its own address."""
    return RedirectResponse(f"/day/{utc_today().isoformat()}", status_code=307)


@app.get("/day/{day}", response_class=HTMLResponse)
def card_of_the_day(request: Request, day: str):
    """The card of the day: the top card of the deck shuffled with the ISO date as the seed,
    the same card `ootk --seed 2026-10-03 --spread 1` draws."""
    try:
        when = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{quoted(day)} is not a date. Use the form 2026-10-03.")
    if when.isoformat() != day:
        raise HTTPException(status_code=404, detail=f"{quoted(day)} is not a date. Use the form 2026-10-03.")
    today = utc_today()
    # A day ahead of UTC is allowed, so it is "today" everywhere on Earth.
    if when > today + timedelta(days=1):
        raise HTTPException(status_code=404, detail="That day's card hasn't been drawn yet.")
    settings = {
        "spread_key": "1", "topic": "", "significator": "", "framework": "auto",
        "mapping_system": DEFAULT_MAPPING, "draw_mode": "seed", "seed": day,
        "output_format": "visual", "selected_cards": "",
    }
    deck = reference_deck()
    card_titles, significator_label = seeded_draw(deck, day, "1", "")
    reading = run_reading(settings, card_titles, significator_label, deck)
    card = reading["spread_results"][0]["card_data"]
    title = card["title"]
    return templates.TemplateResponse(
        request=request,
        name="day.html",
        context={
            "day": when,
            "is_today": when == today,
            "card": card,
            "name": short_card_name(title),
            "image": card_image_url(title, "full"),
            "prompt": reading["analytical_prompt"],
            "reading_url": share_path(settings),
            "previous": (when - timedelta(days=1)).isoformat() if when > date.min else None,
            "next": (when + timedelta(days=1)).isoformat() if when < today else None,
            "today": today.isoformat(),
        },
    )


# ---------- testimonials ----------

TESTIMONIAL_MAX = 600
TESTIMONIAL_NAME_MAX = 60
USER_AGENT_MAX = 200
# A random id per browser, kept for a year, so each visitor session sends at most one
# testimonial. Only /testimonial sets it; it carries nothing but the id.
SESSION_COOKIE = "ootk_session"
SESSION_ID = re.compile(r"[A-Za-z0-9_-]{22}")
SESSION_MAX_AGE = 365 * 24 * 3600
# Approvals reach the front page within this many seconds, without a database query per visit.
TESTIMONIAL_CACHE_SECONDS = 300
# While the database is unreachable, the front page waits this long before trying it again.
# Every other part of the page comes from memory, so it stays instant during an outage.
TESTIMONIAL_RETRY_SECONDS = 60
_testimonial_cache = {}
# Clearing cookies starts a new session, so one address may send at most three an hour.
testimonial_senders = FailedLogins(attempts=3, window=3600)


def visitor_session(request: Request) -> str | None:
    sid = request.cookies.get(SESSION_COOKIE, "")
    return sid if SESSION_ID.fullmatch(sid) else None


def with_session_cookie(request: Request, response, sid: str):
    response.set_cookie(SESSION_COOKIE, sid, max_age=SESSION_MAX_AGE, httponly=True,
                        samesite="lax", secure=request.url.scheme == "https")
    return response


def visitor_hash(request: Request) -> str | None:
    """A keyed hash of the visitor's IP address, so repeat senders can be spotted without
    storing the address. None unless VISITOR_HASH_KEY is set: an unkeyed hash of an IPv4
    address can be reversed by trying them all."""
    key = os.getenv("VISITOR_HASH_KEY")
    if not key:
        return None
    return hmac.new(key.encode(), visitor_address(request).encode(), hashlib.sha256).hexdigest()


def testimonial_of_the_day():
    """One approved testimonial, the same for everyone all day (UTC): they take turns in the
    order they were sent. None when none is approved or the database can't be read, so the
    front page never fails because of it."""
    today = utc_today()
    cached = _testimonial_cache.get("day")
    if cached and cached[0] == today and time.monotonic() < cached[1]:
        return cached[2]
    try:
        with get_db_connection() as conn:
            approved = approved_testimonials(conn)
    except psycopg.Error as e:
        log.warning("testimonials unavailable: %s", e)
        _testimonial_cache["day"] = (today, time.monotonic() + TESTIMONIAL_RETRY_SECONDS, None)
        return None
    pick = approved[today.toordinal() % len(approved)] if approved else None
    _testimonial_cache["day"] = (today, time.monotonic() + TESTIMONIAL_CACHE_SECONDS, pick)
    return pick


def testimonial_page(request: Request, sid: str, status: int = 200, **context):
    response = guide_page(request, "testimonial.html", max_body=TESTIMONIAL_MAX,
                          max_name=TESTIMONIAL_NAME_MAX, **context)
    response.status_code = status
    return with_session_cookie(request, response, sid)


@app.get("/testimonial", response_class=HTMLResponse)
def testimonial_form(request: Request):
    """The form for a testimonial, or a thank-you once this session has sent one."""
    sid = visitor_session(request)
    sent = False
    if sid:
        with get_db_connection() as conn:
            sent = session_has_testimonial(conn, sid)
    return testimonial_page(request, sid or secrets.token_urlsafe(16), sent=sent)


@app.post("/testimonial", response_class=HTMLResponse)
def send_testimonial(request: Request, body: str = Form(""), name: str = Form(""),
                     website: str = Form("")):
    """Saves a testimonial, unapproved, with this session's id. One per session: a second one
    is refused. `website` is a field people never see; bots that fill it in are ignored."""
    sid = visitor_session(request) or secrets.token_urlsafe(16)
    body, name = body.strip(), " ".join(name.split())
    if website:
        return testimonial_page(request, sid, sent=True)
    error = None
    if not body:
        error = "Please write a few words before sending."
    elif "\x00" in body + name:
        error = "The text contains a character that can't be saved. Please retype it."
    elif len(body) > TESTIMONIAL_MAX:
        error = f"Please keep it to {TESTIMONIAL_MAX} characters (this one has {len(body)})."
    elif len(name) > TESTIMONIAL_NAME_MAX:
        error = f"Please keep the name to {TESTIMONIAL_NAME_MAX} characters."
    if error:
        return testimonial_page(request, sid, status=400, error=error, given_body=body, given_name=name)
    visitor = visitor_address(request)
    if testimonial_senders.retry_after(visitor):
        return testimonial_page(request, sid, status=429, given_body=body, given_name=name,
                                error="Several testimonials have come from here recently. "
                                      "Please try again in an hour.")
    user_agent = request.headers.get("user-agent", "")[:USER_AGENT_MAX]
    with get_db_connection() as conn:
        saved = save_testimonial(conn, sid, name, body, user_agent, visitor_hash(request))
    if saved:
        testimonial_senders.failed(visitor)
        log.info("testimonial received, waiting for approval")
    return testimonial_page(request, sid, sent=True, just_sent=saved)


# ---------- admin: approving testimonials ----------

# /admin is linked from nowhere and only works when ADMIN_PASSWORD is set; without it the page
# doesn't exist (404). Signing in sets a cookie derived from the password, so changing the
# password signs every browser out. The cookie is SameSite=Strict, so another site can't make a
# signed-in browser press the buttons.
ADMIN_COOKIE = "ootk_admin"
ADMIN_MAX_AGE = 7 * 24 * 3600
admin_logins = FailedLogins()


def admin_password() -> str:
    password = os.getenv("ADMIN_PASSWORD", "")
    if not password:
        raise HTTPException(status_code=404, detail="There is no page at this address.")
    return password


def admin_token(password: str) -> str:
    return hmac.new(password.encode(), b"ootk-admin-session", hashlib.sha256).hexdigest()


def is_admin(request: Request) -> bool:
    given = request.cookies.get(ADMIN_COOKIE, "")
    return secrets.compare_digest(given.encode(), admin_token(admin_password()).encode())


def admin_page(request: Request, status: int = 200, **context):
    response = guide_page(request, "admin.html", **context)
    response.status_code = status
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    """Sign-in form, or every testimonial with approve, hide and delete buttons."""
    if not is_admin(request):
        return admin_page(request, signed_in=False)
    with get_db_connection() as conn:
        try:
            rows = list_testimonials(conn)
        except psycopg.errors.UndefinedTable as e:
            raise DatabaseOutdated("testimonials table is missing") from e
    return admin_page(request, signed_in=True, testimonials=rows,
                      waiting=sum(not t["approved"] for t in rows))


@app.post("/admin/login")
def admin_login(request: Request, password: str = Form("")):
    expected = admin_password()
    visitor = visitor_address(request)
    wait = admin_logins.retry_after(visitor)
    if wait:
        return locked_out(wait)
    if not secrets.compare_digest(password.encode(), expected.encode()):
        wait = admin_logins.failed(visitor)
        if wait:
            log.warning("admin lockout started for one visitor")
            return locked_out(wait)
        return admin_page(request, status=401, signed_in=False, error="That password isn't right.")
    admin_logins.succeeded(visitor)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(ADMIN_COOKIE, admin_token(expected), max_age=ADMIN_MAX_AGE, httponly=True,
                        samesite="strict", secure=request.url.scheme == "https", path="/admin")
    return response


@app.post("/admin/logout")
def admin_logout(request: Request):
    admin_password()
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie(ADMIN_COOKIE, path="/admin")
    return response


ADMIN_ACTIONS = {"approve", "hide", "delete"}


@app.post("/admin/testimonials/{testimonial_id}")
def admin_testimonial(request: Request, testimonial_id: int, action: str = Form("")):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Sign in at /admin first.")
    if action not in ADMIN_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown action.")
    with get_db_connection() as conn:
        if action == "delete":
            delete_testimonial(conn, testimonial_id)
        else:
            set_testimonial_approved(conn, testimonial_id, action == "approve")
    _testimonial_cache.clear()          # the front page picks the change up straight away
    return RedirectResponse("/admin", status_code=303)


NO_SUCH_REPORT = ("No reading has this link. Check that the whole address was copied; readings "
                  "saved before links were random get theirs from "
                  "database/migrations/add_report_links.sql.")


@app.get("/report/{link}", response_class=HTMLResponse)
def show_report(request: Request, link: str):
    """A saved reading's report, rebuilt from the cards and settings stored with the session."""
    session_id, stored, reading, seed_redraws = saved_reading_parts(link)
    return render_report(request, session_id, stored, reading, json_url=f"/report/{link}/json",
                         seed_redraws=seed_redraws)


@app.get("/report/{link}/json")
def saved_reading_json(link: str):
    """The report's JSON download for a saved reading."""
    _, settings, reading, _ = saved_reading_parts(link)
    return reading_json_response(settings, reading)


def saved_reading_parts(link):
    """(session_id, settings, run_reading() result, whether its seed still draws its cards) for
    a saved report's link; 404 if unknown."""
    if not REPORT_LINK.fullmatch(link):
        raise HTTPException(status_code=404, detail=NO_SUCH_REPORT)
    with get_db_connection() as conn:
        found = load_report_by_link(conn, link)
        if not found:
            raise HTTPException(status_code=404, detail=NO_SUCH_REPORT)
        session_id, stored = found
        stored.pop("link", None)
        if stored.pop("mapping_version", 1) < 2 and stored.get("mapping_system") == "golden_dawn":
            stored["mapping_system"] = "thoth"
        saved_at = stored.pop("saved_at", None)
        seed_redraws = (stored.pop("draw_version", 1) >= DRAW_VERSION
                        or not reshuffles(stored["spread_key"])
                        or (saved_at is not None and saved_at >= RESHUFFLE_SINCE))
        card_titles = stored.pop("card_titles")
        significator_label = stored.pop("significator_label")
    return session_id, stored, run_reading(stored, card_titles, significator_label), seed_redraws


# Which Major carries each sign, per mapping system, for the card panel's small maps. Reference
# data that changes only with a migration, so it is read once per process.
_sign_carriers_cache = {}


def load_sign_carriers(deck, system):
    if system not in _sign_carriers_cache:
        rows = reference_rows(system)
        _sign_carriers_cache[system] = atlas.sign_carriers(
            rows[c["title"]] for c in deck if c["arcana_type"] == "Major" and c["title"] in rows)
    return _sign_carriers_cache[system]


def run_reading(settings, card_titles, significator_label, deck=None):
    """Looks up the drawn cards and runs every analysis. Returns the pieces the report needs."""
    spread_key, mapping_system = settings["spread_key"], settings["mapping_system"]
    selected_spread = SPREADS[spread_key]
    positions = spread_positions(spread_key)
    spread_results = []
    rows = card_rows(card_titles, mapping_system)
    for idx, title in enumerate(card_titles):
        card_data = rows.get(title)
        if not card_data:
            raise HTTPException(
                status_code=400,
                detail=f"Card title {quoted(title)} was not found in the database."
            )
        spread_results.append({
            "position_number": idx + 1,
            "position_name": positions[idx],
            "card_data": card_data
        })

    deck = deck or reference_deck()
    withheld = withheld_cards(deck, card_titles, mapping_system)
    reading = analyze_reading(
        selected_spread["name"], spread_key, settings["topic"], significator_label,
        settings["seed"] or "Graphical Selection", spread_results,
        framework=settings["framework"], mapping_system=mapping_system, withheld=withheld,
    )
    return {
        "spread_name": selected_spread["name"], "significator_label": significator_label,
        "spread_results": spread_results, "withheld": withheld,
        "sign_carriers": load_sign_carriers(deck, mapping_system), **reading,
    }


def report_view(settings, r):
    return build_report_view(settings["spread_key"], r["spread_results"], r["element_counts"],
                             r["dignity_matrix"], r["spatial_matrix"], r["macro_framework"],
                             r["framework_basis"], r.get("sign_carriers"))


def export_reading(settings, r, view):
    return reading_export(r["spread_name"], settings, r["significator_label"],
                          r["macro_framework"], r["framework_basis"], r["element_counts"],
                          r["spread_results"], view, r["dignity_matrix"], r["spatial_matrix"],
                          r["withheld"])


def reading_json_response(settings, r):
    """The report's JSON download, built when asked for rather than embedded in every page."""
    data = export_reading(settings, r, report_view(settings, r))
    return Response(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition":
                             'attachment; filename="ootk_reading.json"'})


def render_report(request, session_id, settings, r, shared=False, json_url=None, unsaved=False,
                  seed_redraws=True):
    """The visual report for a reading from run_reading().

    A full Opening of the Key export is about 300 KB, so a report that has an address of its
    own (json_url) fetches it from there on demand instead of carrying it in the page.
    seed_redraws is False for a saved reading whose seed no longer draws its cards
    (DRAW_VERSION): it then gets no share link or command."""
    spread_key, seed = settings["spread_key"], settings["seed"]
    redraw = bool(seed) and seed_redraws
    mapping_system, framework = settings["mapping_system"], settings["framework"]
    view = report_view(settings, r)
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "session_id": session_id,
            "spread_name": r["spread_name"],
            "topic": settings["topic"],
            "prompt": r["analytical_prompt"],
            "spread_results": r["spread_results"],
            "dignity_matrix": r["dignity_matrix"],
            "element_counts": r["element_counts"],
            "mapping_system": mapping_system,
            "mapping_label": MAPPING_LABELS[mapping_system],
            "significator": r["significator_label"],
            "seed": seed,
            "settings": settings,
            "shared": shared,
            "unsaved": unsaved,
            "share_path": share_path(settings) if redraw else "",
            "cli_command": cli_command(spread_key, seed, mapping_system, framework,
                                       settings["significator"], settings["topic"]) if redraw else "",
            "seed_redraws": seed_redraws,
            "spatial_details": r["spatial_details"],
            "spatial_dist": r["spatial_dist"],
            "solid_counts": r["solid_counts"],
            "topology_details": r["topology_details"],
            "dual_pairings": r["dual_pairings"],
            "withheld": withheld_view(r["withheld"]),
            "view": view,
            "json_url": json_url,
            "reading": None if json_url else export_reading(settings, r, view),
        }
    )
