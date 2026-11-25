"""Static files for the web GUI: versioned URLs, long cache headers and response compression."""
import functools
import gzip
import hashlib
import time

import anyio.to_thread
from starlette.datastructures import Headers, MutableHeaders
from starlette.staticfiles import StaticFiles

from ootk import PROJECT_ROOT

try:
    import brotli
except ImportError:  # gzip only
    brotli = None

STATIC_DIR = PROJECT_ROOT / "static"
# Versioned static URLs never change content, so browsers may keep them for a year.
IMMUTABLE = "public, max-age=31536000, immutable"
UNVERSIONED = "public, max-age=3600"
# Pages, form answers and everything else the app builds: the browser checks back each time
# and shared caches (Cloudflare) never keep a copy, since a page can carry a visitor's own
# question, journal or password-gated content.
DYNAMIC = "private, no-cache"


# A report page asks for a few hundred static URLs (every card image in every size); each
# answer is kept for a moment instead of a file-system stat per call.
URL_TTL = 2.0
URL_CACHE_MAX = 4096       # well above the ~250 files under static/
_url_cache = {}
# Content hash per file, worked out again only when the file's mtime or size changes.
_hash_cache = {}


def _content_version(path):
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    hit = _hash_cache.get(path)
    if hit and hit[0] == key:
        return hit[1]
    version = hashlib.blake2b(path.read_bytes(), digest_size=5).hexdigest()
    if len(_hash_cache) >= URL_CACHE_MAX:
        _hash_cache.clear()
    _hash_cache[path] = (key, version)
    return version


def static_url(relpath):
    """'/static/<relpath>?v=<content hash>', or None when the file is missing.

    The version is a hash of the file's bytes, so it changes exactly when the content does:
    an edited file gets a new URL at once (within URL_TTL seconds), and a deploy that leaves a
    file alone keeps its old URL, so browsers and Cloudflare go on serving their cached copy.
    (An mtime version changed on every deploy, because each build checks the files out anew.)
    """
    now = time.monotonic()
    hit = _url_cache.get(relpath)
    if hit and now - hit[0] < URL_TTL:
        return hit[1]
    try:
        url = f"/static/{relpath}?v={_content_version(STATIC_DIR / relpath)}"
    except OSError:
        url = None
    if len(_url_cache) >= URL_CACHE_MAX:
        _url_cache.clear()
    _url_cache[relpath] = (now, url)
    return url


class CachedStaticFiles(StaticFiles):
    """StaticFiles with a year-long cache for versioned (?v=) URLs and an hour otherwise."""

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        versioned = b"v=" in scope.get("query_string", b"")
        response.headers.setdefault("Cache-Control", IMMUTABLE if versioned else UNVERSIONED)
        return response


THREAD_MINIMUM_SIZE = 128 * 1024
COMPRESSIBLE = ("text/", "application/json", "application/javascript", "image/svg+xml")


class CompressionMiddleware:
    """Brotli (when installed and accepted) or gzip for text responses of 500 bytes or more.

    Buffers the whole body before compressing; every compressible response here (pages,
    markdown, JSON, small CSS/JS files) is small enough for that. Images pass straight through.
    """

    def __init__(self, app, minimum_size=500, brotli_quality=5, gzip_level=6):
        self.app = app
        self.minimum_size = minimum_size
        self.brotli_quality = brotli_quality
        self.gzip_level = gzip_level

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        accept = Headers(scope=scope).get("accept-encoding", "")
        encoding = "br" if brotli and "br" in accept else "gzip" if "gzip" in accept else None
        start, chunks = None, []

        async def wrapped_send(message):
            nonlocal start
            if message["type"] == "http.response.start":
                headers = Headers(raw=message["headers"])
                content_type = headers.get("content-type", "")
                if (message["status"] != 206 and "content-encoding" not in headers
                        and content_type.startswith(COMPRESSIBLE)):
                    if encoding:
                        start = message      # hold it until the body is known
                        return
                    MutableHeaders(scope=message).add_vary_header("Accept-Encoding")
                await send(message)
            elif message["type"] == "http.response.body" and start is not None:
                chunks.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                body = b"".join(chunks)
                headers = MutableHeaders(raw=start["headers"])
                headers.add_vary_header("Accept-Encoding")
                if len(body) >= self.minimum_size:
                    compress = (functools.partial(brotli.compress, quality=self.brotli_quality)
                                if encoding == "br"
                                else functools.partial(gzip.compress, compresslevel=self.gzip_level))
                    # Large reports take a few ms to compress: keep that off the event loop.
                    body = (await anyio.to_thread.run_sync(compress, body)
                            if len(body) >= THREAD_MINIMUM_SIZE else compress(body))
                    headers["Content-Encoding"] = encoding
                    headers["Content-Length"] = str(len(body))
                await send(start)
                await send({"type": "http.response.body", "body": body})
            else:
                await send(message)

        await self.app(scope, receive, wrapped_send)
