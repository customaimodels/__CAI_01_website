"""READ: the public articles at /articles/ (2026-10-14). Static files from this folder only.
Never served: NOTE.md, 04_inspiration/, any .py, any dotfile. Indexed by search engines (public, unlike the vault)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOUNT = "/articles"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".xml": "application/xml",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp",
         ".json": "application/json", ".ico": "image/x-icon", ".mp4": "video/mp4"}
HIDDEN = ("04_inspiration", "redirects.json", "brand.json")   # brand.json = an article's pool receipt, never served
import json as _json
REDIRECTS = _json.loads((HERE / "redirects.json").read_text(encoding="utf-8"))["301"]  # old slug → clean slug (2026-10-17)


def _send(h, code, body, ctype):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", "public, max-age=300")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


ALIASES = {"/yerko-vargas": "/yeriko-vargas/", "/yeriko-vargas": "/yeriko-vargas/"}   # his short link to positions (2026-10-20)


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    to = ALIASES.get(path.rstrip("/")) if method == "GET" else None
    if method == "GET" and path.startswith("/s/"):   # old per-client share links (/s/<client-token>/<project>) → the hub (2026-10-20)
        to = "/r-cai/"
    if to and path != to:                     # site-wide short links: 301 to the one canonical page, query kept
        q = h.path.split("?", 1)[1].split("#", 1)[0] if "?" in h.path else ""
        h.send_response(301)
        h.send_header("Location", to + ("?" + q if q else ""))
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    if method != "GET" or (path != MOUNT and not path.startswith(MOUNT + "/")):
        return False
    old = REDIRECTS.get(path if path.endswith("/") else path + "/")
    if old:                                   # a renamed article: its old URL hands its rank to the new one
        q = h.path.split("?", 1)[1].split("#", 1)[0] if "?" in h.path else ""
        h.send_response(301)
        h.send_header("Location", old + ("?" + q if q else ""))
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    rel = path[len(MOUNT) + 1:]
    if path == MOUNT or (rel and not rel.endswith("/") and (HERE / rel).is_dir()):
        h.send_response(301)
        h.send_header("Location", path + "/")
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    f = (HERE / (rel + "index.html" if rel.endswith("/") or not rel else rel)).resolve()
    parts = f.relative_to(HERE).parts if HERE in f.parents else ()
    if (not parts or not f.is_file() or f.suffix.lower() not in TYPES or any(p.startswith(".") or p in HIDDEN for p in parts)):
        _send(h, 404, b"not found", "text/plain")
        return True
    body = f.read_bytes()
    rng = h.headers.get("Range", "") if f.suffix.lower() == ".mp4" else ""
    if rng.startswith("bytes="):              # Safari plays <video> only from byte ranges (206)
        a, _, b = rng[6:].split(",")[0].partition("-")
        start = int(a) if a else max(0, len(body) - int(b or 0))
        end = min(int(b), len(body) - 1) if a and b else len(body) - 1
        if start >= len(body) or start > end:
            h.send_response(416)
            h.send_header("Content-Range", f"bytes */{len(body)}")
            h.send_header("Content-Length", "0")
            h.end_headers()
            return True
        part = body[start:end + 1]
        h.send_response(206)
        h.send_header("Content-Type", "video/mp4")
        h.send_header("Accept-Ranges", "bytes")
        h.send_header("Content-Range", f"bytes {start}-{end}/{len(body)}")
        h.send_header("Cache-Control", "public, max-age=300")
        h.send_header("Content-Length", str(len(part)))
        h.end_headers()
        h.wfile.write(part)
        return True
    _send(h, 200, body, TYPES[f.suffix.lower()])
    return True
