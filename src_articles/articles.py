"""READ: the public articles at /articles/ (2026-10-14). Static files from this folder only.
Never served: NOTE.md, 04_inspiration/, any .py, any dotfile. Indexed by search engines (public, unlike the vault)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOUNT = "/articles"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".xml": "application/xml",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp",
         ".json": "application/json"}
HIDDEN = ("04_inspiration",)


def _send(h, code, body, ctype):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", "public, max-age=300")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if method != "GET" or (path != MOUNT and not path.startswith(MOUNT + "/")):
        return False
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
    _send(h, 200, f.read_bytes(), TYPES[f.suffix.lower()])
    return True
