"""The portal, mounted at /r-cai on whatever server carries the site (run.py locally, main.py on Railway).

    handle(h, "GET"|"POST") -> True if the request was /r-cai/..., answered here; False = not ours.

GET  /r-cai/            the page (src_rcai/10_web)
POST /r-cai/api/login   {email, code}  → sets the rcai cookie (Path=/r-cai)
GET  /r-cai/api/me      the signed-in view (records re-read every call: the hub is the truth)
POST /r-cai/api/password {current, new} → adds the next pw_N column (05_users), re-issues the cookie
GET  /r-cai/api/master.csv  owners only: the MASTER table, person × project
POST /r-cai/api/logout
"""
import importlib
import json
import mimetypes
import os
from http.cookies import SimpleCookie

C = importlib.import_module("src_rcai.01_config")
R = importlib.import_module("src_rcai.02_records")
A = importlib.import_module("src_rcai.03_auth")
U = importlib.import_module("src_rcai.05_users")
CFG = None


def _cfg():
    global CFG
    CFG = CFG or C.load()
    return CFG


def _send(h, code, body, ctype, cookie=None, cache="no-store"):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", cache)
    h.send_header("X-Frame-Options", "DENY")
    h.send_header("Referrer-Policy", "no-referrer")
    if cookie is not None:
        h.send_header("Set-Cookie", cookie)
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)
    return True


def _json(h, code, obj, cookie=None):
    return _send(h, code, json.dumps(obj).encode(), "application/json", cookie)


def _ip(h):
    """Behind Railway's proxy every visitor shares one socket address: use the forwarded one there."""
    fwd = h.headers.get("X-Forwarded-For", "") if os.environ.get("PORT") else ""
    return fwd.split(",")[0].strip() or h.client_address[0]


def _email(h):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    return A.read(jar["rcai"].value) if "rcai" in jar else None


def _cookie(value, age):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"rcai={value}; Path={C.MOUNT}; Max-Age={age}; HttpOnly; SameSite=Strict{secure}"


def _file(h, rel):
    f = (C.WEB / (rel or "index.html")).resolve()
    if C.WEB.resolve() not in f.parents or not f.is_file():
        return _json(h, 404, {"error": "not found"})
    return _send(h, 200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                 cache="no-cache" if f.suffix == ".html" else "public, max-age=3600")


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if path != C.MOUNT and not path.startswith(C.MOUNT + "/"):
        return False
    if path == C.MOUNT:                                   # relative links need the trailing slash
        h.send_response(301)
        h.send_header("Location", C.MOUNT + "/")
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    rel = path[len(C.MOUNT) + 1:]
    cfg = _cfg()
    if rel.startswith("api/") and not cfg["hub_json"] and not cfg["hub"].exists():
        return _json(h, 503, {"error": "The portal is being set up. Write to customaimodels@gmail.com."})
    if method == "GET":
        if rel == "api/health":
            return _json(h, 200, {"ok": True})
        if rel == "api/me":
            email = _email(h)
            v = R.view(R.load(cfg), cfg, email) if email else None
            if not v:
                return _json(h, 401, {"in": False})
            return _json(h, 200, {"in": True, "stages": R.stages(), "own_pw": U.has_own(email),
                                  "pw_on": U.store() is not None, **v})
        if rel == "api/master.csv":
            email = _email(h)
            if not email or email not in cfg["owners"]:
                return _json(h, 403, {"error": "owners only"})
            h.send_response(200)
            body = U.master_csv(cfg).encode()
            for k, val in (("Content-Type", "text/csv; charset=utf-8"), ("Cache-Control", "no-store"),
                           ("Content-Disposition", 'attachment; filename="R-CAI_MASTER.csv"'), ("Content-Length", str(len(body)))):
                h.send_header(k, val)
            h.end_headers()
            h.wfile.write(body)
            return True
        return _file(h, rel)
    if rel == "api/logout":
        return _json(h, 200, {"in": False}, _cookie("", 0))
    if rel not in ("api/login", "api/password"):
        return _json(h, 404, {"error": "not found"})
    try:
        n = min(int(h.headers.get("Content-Length", 0)), 4096)
        data = json.loads(h.rfile.read(n) or b"{}")
    except (ValueError, json.JSONDecodeError):
        return _json(h, 400, {"error": "bad request"})
    ip = _ip(h)
    if A.locked(cfg, ip):
        return _json(h, 429, {"error": "Too many tries. Wait a few minutes."})
    if rel == "api/password":
        return _password(h, cfg, ip, data)
    email = str(data.get("email", ""))[:120]
    ok = A.check_code(cfg, ip, str(data.get("code", ""))[:128], email)
    v = R.view(R.load(cfg), cfg, email) if ok else None
    A.log(email, bool(v), ip)
    if not v:
        return _json(h, 401, {"error": "That email and code word don't open a hub."})
    return _json(h, 200, {"in": True}, _cookie(A.issue(cfg, email), cfg["session_hours"] * 3600))


def _password(h, cfg, ip, data):
    """Signed in + the current password (or the shared code word) → the next pw_N column. Every other session ends."""
    email = _email(h)
    if not email:
        return _json(h, 401, {"error": "Sign in again."})
    if U.store() is None:
        return _json(h, 503, {"error": "Password changes switch on soon. Write to customaimodels@gmail.com."})
    cur, new = str(data.get("current", ""))[:128], str(data.get("new", ""))[:200]
    if not A.check_code(cfg, ip, cur, email):
        A.log(email, False, ip, "password")
        return _json(h, 403, {"error": "Your current password isn't right."})
    why = U.problem(new, cur)
    if why:
        return _json(h, 400, {"error": why})
    n = U.change(email, new)
    A.log(email, True, ip, f"password v{n}")
    return _json(h, 200, {"ok": True, "version": n}, _cookie(A.issue(cfg, email), cfg["session_hours"] * 3600))
