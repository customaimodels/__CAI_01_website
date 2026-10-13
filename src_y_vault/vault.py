"""_Y_VAULT, mounted at /y-vault on whatever server carries the site (run.py locally, main.py on Railway).

    handle(h, "GET"|"POST") -> True if the request was /y-vault/..., answered here; False = not ours.

GET  /y-vault/              the gate + the shelf (10_web/index.html)
POST /y-vault/api/login     {pin}  → sets the yvault cookie (Path=/y-vault)
GET  /y-vault/api/list      the pages on the shelf: every *.html at this folder's root (signed in only)
GET  /y-vault/<page>.html   one page (signed in only)
POST /y-vault/api/logout

The PIN is config.yml vault_sha256 (or the YVAULT_SHA256 variable). A 4-digit PIN is a curtain, not a lock:
the repo is public, so anything put here can be read on GitHub.
"""
import hashlib
import hmac
import importlib
import json
import os
import re
import time
from http.cookies import SimpleCookie
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
A = importlib.import_module("src_rcai.03_auth")      # same cookie secret as R-CAI
HERE = Path(__file__).resolve().parent
WEB = HERE / "10_web"
MOUNT = "/y-vault"
HOURS, MAX_FAILS, LOCK_MIN = 12, 5, 10
_FAILS = {}
TITLE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def _pin_hash():
    if os.environ.get("YVAULT_SHA256"):
        return os.environ["YVAULT_SHA256"]
    m = re.search(r"^vault_sha256:\s*(\S+)", C.CONFIG.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def pages():
    """The shelf: every *.html at the vault root, in file order. Label = its <title>."""
    out = []
    for f in sorted(HERE.glob("*.html")):
        t = TITLE.search(f.read_text(encoding="utf-8", errors="ignore")[:4000])
        out.append({"file": f.name, "title": (t.group(1).strip() if t else f.stem.strip("_")),
                    "kind": "linkedin" if "linked" in f.name.lower() else "page"})
    return out


def _send(h, code, body, ctype, cookie=None):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", "no-store")
    h.send_header("Referrer-Policy", "no-referrer")
    h.send_header("X-Robots-Tag", "noindex")
    if cookie is not None:
        h.send_header("Set-Cookie", cookie)
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)
    return True


def _json(h, code, obj, cookie=None):
    return _send(h, code, json.dumps(obj).encode(), "application/json", cookie)


def _ip(h):
    fwd = h.headers.get("X-Forwarded-For", "") if os.environ.get("PORT") else ""
    return fwd.split(",")[0].strip() or h.client_address[0]


def _cookie(value, age):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"yvault={value}; Path={MOUNT}; Max-Age={age}; HttpOnly; SameSite=Strict{secure}"


def _issue():
    body = f"vault|{int(time.time() + HOURS * 3600)}"
    return f"{body}|{hmac.new(A._secret(), body.encode(), hashlib.sha256).hexdigest()}"


def _in(h):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    try:
        who, exp, sig = jar["yvault"].value.rsplit("|", 2)
    except (KeyError, ValueError):
        return False
    good = hmac.new(A._secret(), f"{who}|{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good) and int(exp) > time.time()


def _locked(ip):
    now = time.time()
    _FAILS[ip] = [t for t in _FAILS.get(ip, []) if now - t < LOCK_MIN * 60]
    return len(_FAILS[ip]) >= MAX_FAILS


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if path != MOUNT and not path.startswith(MOUNT + "/"):
        return False
    if path == MOUNT:
        h.send_response(301)
        h.send_header("Location", MOUNT + "/")
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    rel = path[len(MOUNT) + 1:]
    if method == "GET":
        if rel in ("", "index.html"):
            return _send(h, 200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if not _in(h):
            return _json(h, 401, {"in": False})
        if rel == "api/list":
            return _json(h, 200, {"in": True, "pages": pages()})
        if rel in {p["file"] for p in pages()}:
            return _send(h, 200, (HERE / rel).read_bytes(), "text/html; charset=utf-8")
        return _json(h, 404, {"error": "not found"})
    if rel == "api/logout":
        return _json(h, 200, {"in": False}, _cookie("", 0))
    if rel != "api/login":
        return _json(h, 404, {"error": "not found"})
    ip = _ip(h)
    if _locked(ip):
        return _json(h, 429, {"error": "Too many tries. Wait a few minutes."})
    try:
        pin = str(json.loads(h.rfile.read(min(int(h.headers.get("Content-Length", 0)), 512)) or b"{}").get("pin", ""))
    except (ValueError, AttributeError):
        return _json(h, 400, {"error": "bad request"})
    want = _pin_hash()
    if not want or not hmac.compare_digest(hashlib.sha256(pin.strip().encode()).hexdigest(), want):
        _FAILS.setdefault(ip, []).append(time.time())
        return _json(h, 401, {"error": "Wrong PIN."})
    return _json(h, 200, {"in": True}, _cookie(_issue(), HOURS * 3600))
