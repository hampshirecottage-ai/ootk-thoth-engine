"""Private reading journals: a person's readings over time, grouped into threads (one per
question or project), each with the AI's answer, their notes and what actually happened.

A journal has no account. It is opened by a secret link (/journal/k/<key>); the database keeps
only a SHA-256 hash of the key, so a copy of the database can't open anyone's journal. The browser
remembers the key in a cookie. Readings themselves stay in tarot_sessions as before; an entry
points at one.

Thread names, answers, notes and outcomes are encrypted here (Fernet, key JOURNAL_KEY) before they
reach the database, so they read as scrambled text in the Neon console. Without JOURNAL_KEY the
site offers no journal at all. Losing JOURNAL_KEY makes every journal's text unreadable, so it
needs a safe second copy.
"""
import hashlib
import os
import re
import secrets
from datetime import date, timedelta

from cryptography.fernet import Fernet, InvalidToken

KEY_BYTES = 24                       # secrets.token_urlsafe(24): 32 characters
KEY_PATTERN = r"[A-Za-z0-9_-]{32}"
NAME_MAX = 200                       # a thread's name (the question or project)
ANSWER_MAX = 200_000                 # an AI's answer, as pasted
NOTE_MAX = 10_000                    # notes, and what actually happened
AI_NAMES = ("Claude", "ChatGPT", "Grok", "Gemini", "Copilot", "Other")
THREADS_MAX = 200                    # per journal
ENTRIES_MAX = 2000                   # per journal
UNUSED_MONTHS = 24                   # a journal nobody opened for this long is deleted


def enabled() -> bool:
    return bool(os.getenv("JOURNAL_KEY", "").strip())


def _fernet() -> Fernet:
    return Fernet(os.getenv("JOURNAL_KEY", "").strip().encode())


def seal(text):
    """Encrypts text for the database; empty or None stays None."""
    if not text:
        return None
    return _fernet().encrypt(text.encode()).decode()


def unseal(token):
    """Decrypts what seal() wrote. A token the key can't open (the key was changed) reads as a
    note saying so, rather than breaking the page."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return "[This text can't be read: the site's journal key has changed.]"


def new_key() -> str:
    return secrets.token_urlsafe(KEY_BYTES)


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# ---------- database ----------

def create_journal(conn, key):
    """Starts a journal for `key`. Also deletes journals nobody has opened for UNUSED_MONTHS,
    so the clean-up needs no scheduled job. Returns the journal_id."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM reading_journals WHERE last_used_at < now() - make_interval(months => %s);",
                    (UNUSED_MONTHS,))
        cur.execute("INSERT INTO reading_journals (key_hash) VALUES (%s) RETURNING journal_id;",
                    (key_hash(key),))
        return cur.fetchone()["journal_id"]


def journals_started_since(conn, minutes):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM reading_journals "
                    "WHERE created_at > now() - make_interval(mins => %s);", (minutes,))
        return cur.fetchone()["n"]


def open_journal(conn, key):
    """The journal_id for `key`, or None. Marks the journal as used (at most once a day)."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("UPDATE reading_journals SET last_used_at = now() WHERE key_hash = %s "
                    "AND last_used_at < now() - interval '1 day';", (key_hash(key),))
        cur.execute("SELECT journal_id FROM reading_journals WHERE key_hash = %s;", (key_hash(key),))
        row = cur.fetchone()
    return row["journal_id"] if row else None


def delete_journal(conn, journal_id):
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM reading_journals WHERE journal_id = %s;", (journal_id,))


def list_threads(conn, journal_id):
    """Threads, most recently active first: thread_id, name, created_at, entries, last_added."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT t.thread_id, t.name, t.created_at, count(e.entry_id) AS entries, "
            "  max(e.added_at) AS last_added "
            "FROM reading_journal_threads t "
            "LEFT JOIN reading_journal_entries e ON e.thread_id = t.thread_id "
            "WHERE t.journal_id = %s GROUP BY t.thread_id "
            "ORDER BY coalesce(max(e.added_at), t.created_at) DESC, t.thread_id DESC;", (journal_id,))
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["name"] = unseal(r["name"])
    return rows


def get_thread(conn, journal_id, thread_id):
    with conn.cursor() as cur:
        cur.execute("SELECT thread_id, name, created_at FROM reading_journal_threads "
                    "WHERE journal_id = %s AND thread_id = %s;", (journal_id, thread_id))
        row = cur.fetchone()
    if not row:
        return None
    return dict(row, name=unseal(row["name"]))


def count_threads(conn, journal_id):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM reading_journal_threads WHERE journal_id = %s;", (journal_id,))
        return cur.fetchone()["n"]


def create_thread(conn, journal_id, name):
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("INSERT INTO reading_journal_threads (journal_id, name) VALUES (%s, %s) "
                    "RETURNING thread_id;", (journal_id, seal(name)))
        return cur.fetchone()["thread_id"]


def rename_thread(conn, journal_id, thread_id, name):
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("UPDATE reading_journal_threads SET name = %s WHERE journal_id = %s AND thread_id = %s;",
                    (seal(name), journal_id, thread_id))
        return cur.rowcount == 1


def delete_thread(conn, journal_id, thread_id):
    """Deletes a thread and the entries in it (the readings themselves stay on the site)."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM reading_journal_threads WHERE journal_id = %s AND thread_id = %s;",
                    (journal_id, thread_id))
        return cur.rowcount == 1


def count_entries(conn, journal_id):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM reading_journal_entries WHERE journal_id = %s;", (journal_id,))
        return cur.fetchone()["n"]


def add_entry(conn, journal_id, session_id, thread_id=None):
    """Files a saved reading in the journal; returns its entry_id. A reading already in the
    journal keeps its entry (moved to `thread_id` when one is given)."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reading_journal_entries (journal_id, session_id, thread_id) VALUES (%s, %s, %s) "
            "ON CONFLICT (journal_id, session_id) DO UPDATE "
            "  SET thread_id = coalesce(EXCLUDED.thread_id, reading_journal_entries.thread_id) "
            "RETURNING entry_id;", (journal_id, session_id, thread_id))
        return cur.fetchone()["entry_id"]


def entry_for_session(conn, journal_id, session_id):
    with conn.cursor() as cur:
        cur.execute("SELECT entry_id, thread_id FROM reading_journal_entries "
                    "WHERE journal_id = %s AND session_id = %s;", (journal_id, session_id))
        row = cur.fetchone()
    return dict(row) if row else None


ENTRY_COLUMNS = (
    "e.entry_id, e.thread_id, e.session_id, e.added_at, e.answer, e.answer_ai, e.notes, e.outcome, "
    "e.outcome_at, s.created_at AS drawn_at, s.report_settings->>'link' AS link, "
    "s.report_settings->>'topic' AS question, s.report_settings->>'spread_key' AS spread_key, "
    "s.report_settings->'card_titles' AS card_titles")


def _entry(row):
    row = dict(row)
    for key in ("answer", "notes", "outcome"):
        row[key] = unseal(row[key])
    row["card_titles"] = list(row["card_titles"] or [])
    return row


def list_entries(conn, journal_id, thread_id=None, unfiled=False):
    """Entries newest first: all of them, one thread's (`thread_id`), or those in no thread."""
    where = "e.journal_id = %s"
    args = [journal_id]
    if thread_id is not None:
        where += " AND e.thread_id = %s"
        args.append(thread_id)
    elif unfiled:
        where += " AND e.thread_id IS NULL"
    with conn.cursor() as cur:
        cur.execute(f"SELECT {ENTRY_COLUMNS} FROM reading_journal_entries e "
                    f"JOIN tarot_sessions s ON s.session_id = e.session_id "
                    f"WHERE {where} ORDER BY e.added_at DESC, e.entry_id DESC;", args)
        return [_entry(r) for r in cur.fetchall()]


def get_entry(conn, journal_id, entry_id):
    with conn.cursor() as cur:
        cur.execute(f"SELECT {ENTRY_COLUMNS} FROM reading_journal_entries e "
                    f"JOIN tarot_sessions s ON s.session_id = e.session_id "
                    f"WHERE e.journal_id = %s AND e.entry_id = %s;", (journal_id, entry_id))
        row = cur.fetchone()
    return _entry(row) if row else None


def update_entry(conn, journal_id, entry_id, answer, answer_ai, notes, outcome, thread_id):
    """Saves an entry's texts. outcome_at is set when an outcome is first written and cleared
    with it."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "UPDATE reading_journal_entries SET answer = %s, answer_ai = %s, notes = %s, thread_id = %s, "
            "  outcome_at = CASE WHEN %s::text IS NULL THEN NULL ELSE coalesce(outcome_at, now()) END, "
            "  outcome = %s "
            "WHERE journal_id = %s AND entry_id = %s;",
            (seal(answer), answer_ai or None, seal(notes), thread_id, seal(outcome), seal(outcome),
             journal_id, entry_id))
        return cur.rowcount == 1


def delete_entry(conn, journal_id, entry_id):
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM reading_journal_entries WHERE journal_id = %s AND entry_id = %s;",
                    (journal_id, entry_id))
        return cur.rowcount == 1


# ---------- export ----------

def export_markdown(threads, entries, spread_label=str):
    """The whole journal as one Markdown file: each thread, then its entries oldest first."""
    groups = [(t["thread_id"], t["name"]) for t in threads] + [(None, "Not in a thread")]
    out = ["# My reading journal", ""]
    for thread_id, name in groups:
        mine = sorted((e for e in entries if e["thread_id"] == thread_id), key=lambda e: e["added_at"])
        if not mine and thread_id is None:
            continue
        out += [f"## {name}", ""]
        for e in mine:
            out += [f"### {e['drawn_at']:%d %B %Y} · {spread_label(e['spread_key'])}", ""]
            if e["question"]:
                out += [f"**Question:** {e['question']}", ""]
            out += [f"**Cards:** {', '.join(e['card_titles'])}", ""]
            if e["answer"]:
                out += [f"**AI answer{' (' + e['answer_ai'] + ')' if e['answer_ai'] else ''}:**", "", e["answer"], ""]
            if e["notes"]:
                out += ["**Notes:**", "", e["notes"], ""]
            if e["outcome"]:
                out += [f"**What happened** ({e['outcome_at']:%d %B %Y}):", "", e["outcome"], ""]
    return "\n".join(out).rstrip() + "\n"


# ---------- timing windows and the timeline ----------

WINDOWS_MAX = 30                      # per entry
WINDOW_LABEL_MAX = 120


def list_windows(conn, journal_id, entry_id=None):
    """Timing windows (window_id, entry_id, label, starts, ends) of one entry or the whole journal."""
    where, args = "e.journal_id = %s", [journal_id]
    if entry_id is not None:
        where += " AND w.entry_id = %s"
        args.append(entry_id)
    with conn.cursor() as cur:
        cur.execute("SELECT w.window_id, w.entry_id, w.label, w.starts, w.ends FROM reading_journal_windows w "
                    f"JOIN reading_journal_entries e ON e.entry_id = w.entry_id WHERE {where} "
                    "ORDER BY w.starts, w.window_id;", args)
        return [dict(r, label=unseal(r["label"])) for r in cur.fetchall()]


def replace_windows(conn, journal_id, entry_id, windows):
    """Sets an entry's windows to `windows` [(label, starts, ends)], replacing what was there."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("SELECT 1 FROM reading_journal_entries WHERE journal_id = %s AND entry_id = %s;",
                    (journal_id, entry_id))
        if not cur.fetchone():
            return False
        cur.execute("DELETE FROM reading_journal_windows WHERE entry_id = %s;", (entry_id,))
        for label, starts, ends in windows[:WINDOWS_MAX]:
            cur.execute("INSERT INTO reading_journal_windows (entry_id, label, starts, ends) "
                        "VALUES (%s, %s, %s, %s);", (entry_id, seal(label), starts, ends))
        return True


MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_TO = r"\s*(?:to|through|until|till|-|–|—)\s*"
# "Nov 12 to Nov 22", "12 November – 22 November", "Nov 12-22", "12-22 Nov"
_RANGES = (
    re.compile(rf"\b{_MON}\.?\s+{_DAY}{_TO}(?:{_MON}\.?\s+)?{_DAY}\b", re.I),       # Mon d to [Mon] d
    re.compile(rf"\b{_DAY}\s+{_MON}\.?{_TO}{_DAY}\s+{_MON}\b", re.I),             # d Mon to d Mon
    re.compile(rf"\b{_DAY}{_TO}{_DAY}\s+{_MON}\b", re.I),                          # d-d Mon
)


def _month(name):
    return MONTHS.index(name[:3].lower()) + 1


def _label(line, match_start):
    """The words before a date range on its line, without Markdown marks, as the window's name."""
    text = line[:match_start]
    text = re.sub(r"[*_`#>|]+", " ", text)
    text = re.sub(r"^\s*(?:[-+•]|\d+[.)])\s*", "", text)
    text = re.sub(r"\(\s*$", "", text)
    text = " ".join(text.split()).strip(" :–—-,(")
    for word in (" from", " between", " around", " during", " on", " is", " runs"):
        if text.lower().endswith(word):
            text = text[: -len(word)].rstrip(" :–—-,")
    return text[:WINDOW_LABEL_MAX]


_TIMELINE_HEAD = re.compile(r"^\s*(?:#{1,6}\s*|\*\*)\s*Timeline\b", re.I)
_ANY_HEAD = re.compile(r"^\s*(?:#{1,6}\s|\*\*[^*]+\*\*\s*$)")
_ISO = r"(\d{4})-(\d{1,2})-(\d{1,2})"
_ISO_RANGE = re.compile(rf"{_ISO}(?:\s*(?:to|through|until|–|—|-)\s*{_ISO})?")


def timeline_windows(text):
    """The windows listed under the `## Timeline` heading the prompt asks the AI to end with,
    as (label, starts, ends), or [] when the answer has no such list with dates in it."""
    found, inside = [], False
    for line in (text or "").splitlines():
        if _TIMELINE_HEAD.match(line):
            inside, found = True, []           # the last Timeline list in the answer wins
            continue
        if not inside:
            continue
        if _ANY_HEAD.match(line):
            inside = False
            continue
        m = _ISO_RANGE.search(line)
        if not m:
            continue
        g = [int(x) if x else None for x in m.groups()]
        try:
            starts = date(g[0], g[1], g[2])
            ends = date(g[3], g[4], g[5]) if g[3] else starts
        except ValueError:
            continue
        if ends < starts:
            starts, ends = ends, starts
        found.append((_label(line, m.start()) or "Window", starts, ends))
    seen, out = set(), []
    for w in found:
        if w[1:] not in seen:
            seen.add(w[1:])
            out.append(w)
    return out[:WINDOWS_MAX]


def find_windows(text, after):
    """Date ranges an AI answer names, as (label, starts, ends). The `## Timeline` list the
    prompt asks for is used when there is one; otherwise ranges anywhere in the answer are
    found, with the year filled in: each taken as the next one on or after `after` (the day
    the cards were drawn). Lines without words before the date get "Window" as their name."""
    listed = timeline_windows(text)
    if listed:
        return listed
    found, seen = [], set()
    for line in (text or "").splitlines():
        for pattern in _RANGES:
            for m in pattern.finditer(line):
                g = m.groups()
                try:
                    if pattern is _RANGES[0]:
                        m1, d1, m2, d2 = _month(g[0]), int(g[1]), _month(g[2] or g[0]), int(g[3])
                    elif pattern is _RANGES[1]:
                        d1, m1, d2, m2 = int(g[0]), _month(g[1]), int(g[2]), _month(g[3])
                    else:
                        d1, d2, m1 = int(g[0]), int(g[1]), _month(g[2])
                        m2 = m1
                    # The next such range from the draw; a start up to a month before the draw
                    # (a window already open when the cards were drawn) stays in the draw's year.
                    year = after.year
                    if date(year, m1, 1) < date(after.year, after.month, 1) and (after.month - m1) % 12 > 1:
                        year += 1
                    starts = date(year, m1, d1)
                    ends = date(year + (1 if (m2, d2) < (m1, d1) else 0), m2, d2)
                except ValueError:
                    continue
                if (starts, ends) in seen:
                    continue
                seen.add((starts, ends))
                found.append((_label(line, m.start()) or "Window", starts, ends))
        if len(found) >= WINDOWS_MAX:
            break
    return found[:WINDOWS_MAX]


SIGNS = (("Aries", "♈"), ("Taurus", "♉"), ("Gemini", "♊"), ("Cancer", "♋"), ("Leo", "♌"), ("Virgo", "♍"),
         ("Libra", "♎"), ("Scorpio", "♏"), ("Sagittarius", "♐"), ("Capricorn", "♑"), ("Aquarius", "♒"),
         ("Pisces", "♓"))
SIGN_ELEMENT = ("fire", "earth", "air", "water") * 3


def _add_months(day, n):
    y, m = divmod(day.month - 1 + n, 12)
    return date(day.year + y, m + 1, 1)


def build_timeline(threads, entries, windows, today, spread_label=str):
    """Everything the timeline page draws, with positions as percentages of its width.

    The span runs from the month of the earliest marker (or this month) for at least twelve
    months, to the month after the last one. Rows are grouped by thread; each timing window is a
    row (a bar, or a dot when it is one day), and a reading with no windows is a row with a dot
    on the day it was drawn."""
    from ootk.decans import _sun_reaches   # the Sun's sign changes, worked out as on /day

    dates = [today] + [w["starts"] for w in windows] + [w["ends"] for w in windows] \
        + [e["drawn_at"].date() for e in entries]
    start = date(min(dates).year, min(dates).month, 1)
    end = max(_add_months(start, 12), _add_months(max(dates), 1))
    end = min(end, _add_months(start, 60))           # five years at most on one page
    span = (end - start).days

    def pos(day):
        return max(0.0, min(100.0, (day - start).days / span * 100))

    months, m = [], start
    while m < end:
        nxt = _add_months(m, 1)
        months.append({"label": m.strftime("%b"), "year": m.year if m.month == 1 or m == start else None,
                       "left": pos(m), "width": pos(nxt) - pos(m)})
        m = nxt
    signs = []
    for year in range(start.year - 1, end.year + 1):
        for i, (name, glyph) in enumerate(SIGNS):
            s = _sun_reaches(i * 30, year).date()
            e = _sun_reaches((i + 1) * 30, year).date()
            if e <= start or s >= end:
                continue
            signs.append({"name": name, "glyph": glyph, "short": name[:3], "element": SIGN_ELEMENT[i],
                          "left": pos(max(s, start)), "width": pos(min(e, end)) - pos(max(s, start)),
                          "dates": f"{s:%-d %b} to {e - timedelta(days=1):%-d %b}"})
    by_entry = {}
    for w in windows:
        by_entry.setdefault(w["entry_id"], []).append(w)

    def entry_info(e):
        return {"entry_id": e["entry_id"], "link": e["link"], "question": e["question"],
                "spread": spread_label(e["spread_key"]), "drawn": f"{e['drawn_at']:%-d %b %Y}",
                "cards": ", ".join(e["card_titles"][:6]) + (" …" if len(e["card_titles"]) > 6 else ""),
                "ai": e["answer_ai"] or ""}

    ingresses = sorted((_sun_reaches(i * 30, y).date(), i) for y in range(start.year - 1, end.year + 1)
                       for i in range(12))

    def element(day):
        i = [k for d, k in ingresses if d <= day][-1]
        return SIGN_ELEMENT[i]

    groups = []
    order = [(t["thread_id"], t["name"]) for t in threads] + [(None, "Not in a thread")]
    for thread_id, name in order:
        rows = []
        for e in sorted((e for e in entries if e["thread_id"] == thread_id), key=lambda e: e["drawn_at"]):
            info = entry_info(e)
            mine = by_entry.get(e["entry_id"], [])
            if not mine:
                d = e["drawn_at"].date()
                rows.append(dict(info, label=info["spread"], kind="reading", left=pos(d), width=0, element=element(d),
                                 when=f"Drawn {d:%-d %b %Y}", sort=d))
            for w in mine:
                one_day = w["starts"] == w["ends"]
                rows.append(dict(info, label=w["label"], kind="dot" if one_day else "bar", left=pos(w["starts"]),
                                 element=element(w["starts"]),
                                 width=0 if one_day else pos(w["ends"] + timedelta(days=1)) - pos(w["starts"]),
                                 when=(f"{w['starts']:%-d %b}" if one_day else
                                       f"{w['starts']:%-d %b} to {w['ends']:%-d %b}") + f" {w['ends']:%Y}",
                                 sort=w["starts"]))
        if rows:
            rows.sort(key=lambda r: r["sort"])
            groups.append({"thread_id": thread_id, "name": name, "rows": rows})
    return {"months": months, "signs": signs, "groups": groups, "today": pos(today),
            "months_count": len(months), "start": start, "end": end}
