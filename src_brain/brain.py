"""/brain (2026-10-24): one box, one Send. Each thought = one .txt in his Google Drive, _BRAIN_/_0_random_thaught_txt/.
Not the Y-BRAIN (__Ydta brain.pkl): this is a phone inbox for raw thoughts. Stdlib only.

GET  /brain/                 the box (PIN asked once, then a 365-day cookie on that phone)
POST /brain/login            {pin} → the ybrain cookie (Path=/brain). 5 wrong = that IP locked 10 min
POST /brain/api/save         {text} → Drive upload → {ok, name}. Signed in only, X-Brain: 1 header, 20 KB max
POST /brain/mcp/<secret>     the Claude custom connector (src_brain/connector.py): one MCP tool, save_thought
GET  /brain/manifest.webmanifest   Add to Home Screen = full screen

Secrets live ONLY in env vars (Railway) or 0600 files under dta/_1_processed/brain/ (local, gitignored, never bundled):
    BRAIN_PIN_HASH            PBKDF2 hash (src_util_auth/codes.make) -- set by run.py --brain-pin, typed hidden
    BRAIN_GDRIVE_CLIENT_ID · BRAIN_GDRIVE_CLIENT_SECRET · BRAIN_GDRIVE_REFRESH_TOKEN   run.py --brain-drive-login
    BRAIN_GDRIVE_FOLDER_ID    optional: skips the folder lookup on a cold start
Scope = drive (CHANGED 2026-10-24, his word): the connector writes into a folder HE made (_txt_claude, synced from
the Mac), which drive.file can never see. Cost: a leaked refresh token reads his whole Drive. The code only writes,
only into the fixed _txt_claude id or the _BRAIN_ path; it never reads, lists outside a name check, or deletes.
Missing PIN hash = every login refused. Missing Drive token = Send answers "Drive not connected" and the text stays.
"""
import hashlib
import hmac
import importlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path
from zoneinfo import ZoneInfo

A = importlib.import_module("src_rcai.03_auth")         # _secret(): RCAI_SECRET, the site's cookie secret
K = importlib.import_module("src_util_auth.codes")      # make / _parse: the PBKDF2 used by every door
HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent / "dta" / "_1_processed" / "brain"
MOUNT = "/brain"
FOLDERS = ("_BRAIN_", "_0_random_thaught_txt")          # his spelling, on purpose
TZ = ZoneInfo("America/Detroit")
COOKIE_DAYS, MAX_FAILS, LOCK_MIN, MAX_BYTES = 365, 5, 10, 20_000
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink"
_FAILS, _CACHE, _LOCK = {}, {}, threading.Lock()


# -- secrets: env wins (hosted), else the local 0600 file -------------------------------------------------------
def _env(name):
    if name in os.environ:
        return os.environ[name].strip()
    if os.environ.get("PORT"):                          # hosted: the variable or nothing
        return ""
    try:
        return str(json.loads((LOCAL / "secrets.json").read_text(encoding="utf-8")).get(name, "")).strip()
    except (OSError, ValueError):
        return ""


def save_local(**kv):
    """Write names → values into dta/_1_processed/brain/secrets.json (0600) + railway.env. Prints nothing secret."""
    LOCAL.mkdir(parents=True, exist_ok=True)
    f = LOCAL / "secrets.json"
    try:
        cur = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    cur.update({k: v for k, v in kv.items() if v})
    f.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    f.chmod(0o600)
    env = LOCAL / "railway.env"
    env.write_text("".join(f"{k}={v}\n" for k, v in cur.items()), encoding="utf-8")
    env.chmod(0o600)
    return [f, env]


# -- the PIN + the cookie ------------------------------------------------------------------------------------
def _pin_hash():
    return _env("BRAIN_PIN_HASH")


def _key():
    fp = hashlib.sha256(_pin_hash().encode()).hexdigest()[:24].encode()
    return hmac.new(A._secret(), b"role:brain:v1|" + fp, hashlib.sha256).digest()


def _token():
    body = f"brain|{int(time.time() + COOKIE_DAYS * 86400)}"
    return f"{body}|{hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()}"


def signed_in(h):
    if not K._parse(_pin_hash()):
        return False
    c = SimpleCookie(h.headers.get("Cookie", ""))
    tok = c["ybrain"].value if "ybrain" in c else ""
    try:
        role, exp, sig = tok.split("|")
        good = hmac.new(_key(), f"{role}|{exp}".encode(), hashlib.sha256).hexdigest()
        return role == "brain" and hmac.compare_digest(sig, good) and int(exp) > time.time()
    except ValueError:
        return False


def check_pin(pin):
    parsed = K._parse(_pin_hash())
    word = K.normalize(pin)
    if not parsed or len(word) < 4:
        return False
    rounds, salt, dk = parsed
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", word.encode(), salt, rounds, len(dk)), dk)


def _ip(h):
    return (h.headers.get("X-Forwarded-For", "") or h.client_address[0]).split(",")[0].strip()


def _locked(ip):
    now = time.time()
    _FAILS[ip] = [t for t in _FAILS.get(ip, []) if now - t < LOCK_MIN * 60]
    return len(_FAILS[ip]) >= MAX_FAILS


# -- Drive: one access token + one folder id, cached for the life of the process ------------------------------
def _post(url, data, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _access():
    with _LOCK:
        if _CACHE.get("exp", 0) > time.time() + 60:
            return _CACHE["tok"]
        rid, sec, ref = (_env(n) for n in ("BRAIN_GDRIVE_CLIENT_ID", "BRAIN_GDRIVE_CLIENT_SECRET", "BRAIN_GDRIVE_REFRESH_TOKEN"))
        if not (rid and ref):
            raise RuntimeError("Drive not connected")
        body = urllib.parse.urlencode({"client_id": rid, "client_secret": sec, "refresh_token": ref,
                                       "grant_type": "refresh_token"}).encode()
        t = _post(TOKEN_URL, body)
        _CACHE.update(tok=t["access_token"], exp=time.time() + int(t.get("expires_in", 3600)))
        return _CACHE["tok"]


def _find_or_make(name, parent, tok):
    q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and "
         + (f"'{parent}' in parents" if parent else "'root' in parents"))
    url = API + "?" + urllib.parse.urlencode({"q": q, "fields": "files(id)", "spaces": "drive"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"}), timeout=20) as r:
        hit = json.loads(r.read()).get("files", [])
    if hit:
        return hit[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent] if parent else []}
    return _post(API + "?fields=id", json.dumps(meta).encode(),
                 {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})["id"]


def _folder(tok, folders=FOLDERS):
    """Folder id for a path of names under My Drive, made if missing, cached per path.
    drive.file scope: the app only sees folders IT made, so a hand-made folder of the same name is never found (a twin appears)."""
    if isinstance(folders, str):                         # a fixed folder id (the connector's _txt_claude): no lookup
        return folders
    key = "folder:" + "/".join(folders)
    with _LOCK:
        if _CACHE.get(key):
            return _CACHE[key]
    fid = _env("BRAIN_GDRIVE_FOLDER_ID") if folders == FOLDERS else ""
    if not fid:
        parent = None
        for name in folders:
            parent = _find_or_make(name, parent, tok)
        fid = parent
    with _LOCK:
        _CACHE[key] = fid
    return fid


def save_file(text, now=None, suffix=""):
    """One thought → one .txt in Drive (the /brain page). Returns {name, id, link}."""
    now = now or datetime.now(TZ)
    name = now.strftime("%Y-%m-%d_%H-%M-%S") + (f"_{suffix}" if suffix else "") + ".txt"
    return upload(name, f"{text.strip()}\n\n---\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")


def exists(name, folder_id):
    """True if a live file of this exact name already sits in that folder (so a send never lands a twin)."""
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{safe}' and '{folder_id}' in parents and trashed = false"
    url = API + "?" + urllib.parse.urlencode({"q": q, "fields": "files(id)", "spaces": "drive"})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_access()}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return bool(json.loads(r.read()).get("files"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Drive said {e.code}")
    except urllib.error.URLError:
        raise RuntimeError("Drive unreachable")


def upload(name, body_txt, folders=FOLDERS, mime="text/plain"):
    """One file → Drive, in the folder path `folders`. Returns {name, id, link}. Raises RuntimeError with a short reason."""
    for attempt in (1, 2):                               # a stale token or folder id gets one fresh retry
        try:
            tok = _access()
            meta = {"name": name, "parents": [_folder(tok, folders)], "mimeType": mime}
            b = "brainboundary7f3a"
            payload = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                       f"--{b}\r\nContent-Type: {mime}; charset=UTF-8\r\n\r\n").encode() + body_txt.encode() + f"\r\n--{b}--".encode()
            got = _post(UPLOAD, payload, {"Authorization": f"Bearer {tok}", "Content-Type": f"multipart/related; boundary={b}"})
            fid = got.get("id", "")
            return {"name": name, "id": fid,
                    "link": got.get("webViewLink") or (f"https://drive.google.com/file/d/{fid}/view" if fid else "")}
        except urllib.error.HTTPError as e:
            with _LOCK:
                _CACHE.clear()
            if attempt == 2:
                raise RuntimeError(f"Drive said {e.code}")
        except urllib.error.URLError:
            if attempt == 2:
                raise RuntimeError("Drive unreachable")
    raise RuntimeError("not saved")


def save(text, now=None):
    """The page's door: one thought → one .txt, returns the file name."""
    return save_file(text, now)["name"]


def drive_login():
    """Once, on his Mac: a Desktop OAuth client JSON ({"installed": …}) from ___In_out_bound_ARCH or
    dta/_1_processed/brain/client.json → consent as ygvargas93 (drive) → refresh token saved 0600. Returns a line."""
    import base64
    import http.server
    import secrets
    import shutil
    import socket
    import subprocess
    client = LOCAL / "client.json"
    inbound = HERE.parents[1] / "___In_out_bound_ARCH"
    hits = [p for p in inbound.glob("*.json") if '"installed"' in p.read_text(encoding="utf-8", errors="ignore")] if inbound.is_dir() else []
    if hits and not client.exists():
        LOCAL.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(max(hits, key=lambda p: p.stat().st_mtime), client)
        client.chmod(0o600)
    if not client.exists():
        return "✗ no Desktop OAuth client JSON (drop it in ___In_out_bound_ARCH, then run again)"
    cl = json.loads(client.read_text())["installed"]
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    redirect, verifier, state = f"http://127.0.0.1:{port}/", secrets.token_urlsafe(64), secrets.token_urlsafe(16)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cl["client_id"], "redirect_uri": redirect, "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive", "access_type": "offline", "prompt": "consent",
        "state": state, "login_hint": "ygvargas93@gmail.com",
        "code_challenge": b64(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if q.get("state") == state:
                got.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<p style='font:16px system-ui'>Done. Close this tab.</p>")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    srv.timeout = 300
    subprocess.run(["open", "-na", "Google Chrome", "--args", "--profile-directory=Default", url], check=False)
    srv.handle_request()
    srv.server_close()
    if "code" not in got:
        return "✗ no consent came back (" + got.get("error", "timed out") + ")"
    tok = _post(TOKEN_URL, urllib.parse.urlencode({"code": got["code"], "client_id": cl["client_id"],
        "client_secret": cl.get("client_secret", ""), "redirect_uri": redirect, "grant_type": "authorization_code",
        "code_verifier": verifier}).encode())
    if "refresh_token" not in tok:
        return "✗ Google gave no refresh token"
    save_local(BRAIN_GDRIVE_CLIENT_ID=cl["client_id"], BRAIN_GDRIVE_CLIENT_SECRET=cl.get("client_secret", ""),
               BRAIN_GDRIVE_REFRESH_TOKEN=tok["refresh_token"])
    return "✓ Drive connected (drive) · values for Railway in dta/_1_processed/brain/railway.env"


# -- the page ------------------------------------------------------------------------------------------------
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#0f0a17">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="Brain">
<link rel="manifest" href="/brain/manifest.webmanifest"><link rel="apple-touch-icon" sizes="180x180" href="/03_img/apple-touch-icon.png?v=k1">
<link rel="icon" href="/favicon.ico?v=k1" sizes="any"><title>Brain</title>
<style>*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0;height:100%;background:#0f0a17;color:#ece8f2}
body{font:17px/1.45 -apple-system,system-ui,sans-serif;display:flex;flex-direction:column;min-height:100dvh;
padding:max(1rem,env(safe-area-inset-top)) 1rem max(1rem,env(safe-area-inset-bottom))}
h1{margin:0 0 .8rem;font:600 1.05rem/1 -apple-system,system-ui,sans-serif;color:#a79fb5;letter-spacing:.02em}
textarea,input{width:100%;font-size:17px;color:#ece8f2;background:#1a1226;border:1px solid #3a2d4d;border-radius:14px;padding:1rem}
textarea{flex:1;min-height:40vh;resize:none;line-height:1.5}textarea:focus,input:focus{outline:none;border-color:#f2cd57}
button{margin-top:.8rem;width:100%;min-height:58px;border:0;border-radius:14px;background:#f2cd57;color:#0f0a17;
font:700 1.1rem -apple-system,system-ui,sans-serif;touch-action:manipulation}button:active{opacity:.85}
.say{min-height:1.4em;margin-top:.7rem;text-align:center;color:#a79fb5}.say.ok{color:#9be3a1}.say.bad{color:#ff8a8a}
form{display:flex;flex-direction:column;flex:1}</style></head><body>"""

BOX = HEAD + """<h1>What's on your mind?</h1>
<form id="f"><textarea id="t" autofocus enterkeyhint="send" maxlength="20000" aria-label="What's on your mind?"></textarea>
<button id="b" type="submit">Send</button><p class="say" id="s" role="status"></p></form>
<script>(function(){var f=document.getElementById("f"),t=document.getElementById("t"),b=document.getElementById("b"),s=document.getElementById("s"),busy=0;
t.focus();f.addEventListener("submit",function(e){e.preventDefault();var v=t.value;if(!v.trim()||busy)return;busy=1;
b.textContent="Saving…";s.className="say";s.textContent="";
fetch("/brain/api/save",{method:"POST",headers:{"Content-Type":"application/json","X-Brain":"1"},body:JSON.stringify({text:v})})
.then(function(r){return r.json().then(function(j){return[r.ok,j]})}).then(function(x){busy=0;
if(x[0]){t.value="";b.textContent="Send";s.className="say ok";s.textContent="Saved ✓";t.focus()}
else{if(x[1].error==="sign in")location.reload();b.textContent="Retry";s.className="say bad";s.textContent=x[1].error||"Not saved"}})
.catch(function(){busy=0;b.textContent="Retry";s.className="say bad";s.textContent="No connection. Your text is still here."})})})()</script></body></html>"""

GATE = HEAD + """<h1>Brain</h1><form method="post" action="/brain/login" style="flex:0">
<input name="pin" type="password" inputmode="numeric" autocomplete="current-password" placeholder="PIN" aria-label="PIN" autofocus maxlength="40">
<button type="submit">Open</button><p class="say bad">@@MSG@@</p></form></body></html>"""

MANIFEST = {"name": "Brain", "short_name": "Brain", "start_url": "/brain/", "scope": "/brain/", "display": "standalone",
            "background_color": "#0f0a17", "theme_color": "#0f0a17",
            "icons": [{"src": "/03_img/apple-touch-icon.png?v=k1", "sizes": "180x180", "type": "image/png"}]}


def _send(h, code, body, ctype="text/html; charset=utf-8", extra=()):
    data = body if isinstance(body, bytes) else body.encode()
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(data)))
    h.send_header("Cache-Control", "no-store")
    h.send_header("X-Robots-Tag", "noindex, nofollow")
    h.send_header("X-Frame-Options", "DENY")
    h.send_header("Referrer-Policy", "no-referrer")
    for k, v in extra:
        h.send_header(k, v)
    h.end_headers()
    h.wfile.write(data)
    return True


def _json(h, code, obj):
    return _send(h, code, json.dumps(obj), "application/json")


def _secure(h):
    return "; Secure" if os.environ.get("PORT") else ""


def handle(h, method):
    path = h.path.split("?", 1)[0]
    if path.startswith(MOUNT + "/mcp/") or path == MOUNT + "/mcp":     # the Claude connector (2026-10-24), its own door
        return importlib.import_module("src_brain.connector").handle(h, method)
    if path == MOUNT:
        return _send(h, 301, "", extra=(("Location", MOUNT + "/"),))
    if not path.startswith(MOUNT + "/"):
        return False
    if method == "GET" and path == MOUNT + "/manifest.webmanifest":
        return _send(h, 200, json.dumps(MANIFEST), "application/manifest+json")
    if method == "GET" and path == MOUNT + "/":
        return _send(h, 200, BOX if signed_in(h) else GATE.replace("@@MSG@@", ""))
    if method == "POST" and path == MOUNT + "/login":
        ip = _ip(h)
        n = min(int(h.headers.get("Content-Length") or 0), 2000)
        pin = urllib.parse.parse_qs(h.rfile.read(n).decode("utf-8", "ignore")).get("pin", [""])[0]
        if _locked(ip):
            return _send(h, 429, GATE.replace("@@MSG@@", "Too many tries. Wait 10 minutes."))
        if not check_pin(pin):
            _FAILS.setdefault(ip, []).append(time.time())
            return _send(h, 401, GATE.replace("@@MSG@@", "Wrong PIN."))
        _FAILS.pop(ip, None)
        cookie = f"ybrain={_token()}; Path={MOUNT}; Max-Age={COOKIE_DAYS * 86400}; HttpOnly; SameSite=Strict{_secure(h)}"
        return _send(h, 303, "", extra=(("Location", MOUNT + "/"), ("Set-Cookie", cookie)))
    if method == "POST" and path == MOUNT + "/api/save":
        if h.headers.get("X-Brain") != "1" or not signed_in(h):
            return _json(h, 401, {"error": "sign in"})
        n = int(h.headers.get("Content-Length") or 0)
        if n > MAX_BYTES:
            return _json(h, 413, {"error": "Too long"})
        try:
            text = str(json.loads(h.rfile.read(n) or b"{}").get("text", ""))
        except ValueError:
            return _json(h, 400, {"error": "Not saved"})
        if not text.strip():
            return _json(h, 400, {"error": "Empty"})
        try:
            return _json(h, 200, {"ok": True, "name": save(text)})
        except RuntimeError as e:
            return _json(h, 502, {"error": str(e)})
    return _send(h, 404, "Not found", "text/plain")
