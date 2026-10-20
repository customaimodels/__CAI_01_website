"""RECRUITER, mounted at /recruiter (2026-10-16). One site, three policies:
    /behind-the-models/   public, indexable          (src_resume, via src_y_vault/vault.py public=True)
    /recruiter/           a recruiter's own link     (this file)
    /y-vault/             the owner's PIN            (src_y_vault/vault.py)

POST /recruiter/login       {code} the shared code word → the yrec cookie, 14 days. Its PBKDF2 hash lives ONLY in the
                            Railway variable RECRUITER_CODE_HASH (src_util_auth/codes.py); none set = every login refused
GET /recruiter/in/<token>   a link he minted (run.py --recruiter-link): sets the yrec cookie (Path=/recruiter) → /recruiter/
GET /recruiter/...          the APPROVED pages only (signed in); everything else 401
GET /recruiter/out          clears the cookie

Tokens: rec|<id>|<expiry>|sig, signed with a key derived from RCAI_SECRET + the code hash for this role alone (rotating
the code ends every recruiter session and link) -- it never verifies
as R-CAI or the vault, and theirs never verify here. One link per recruiter, 30 days at most, revocable by id
(RECRUITER_REVOKED on Railway, dta/_1_processed/recruiter/revoked.txt locally).

Content = 20_approved/ (index.html + its files), filled ONLY with what he approved. It never ships raw: the repo is
public, so --bundle seals it into 30_sealed/approved.bin (key = RCAI_DOC_KEY, the handbook key). Empty = "nothing shared".
"""
import base64
import hashlib
import hmac
import importlib
import json
import os
import re
import secrets
import time
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs

A = importlib.import_module("src_rcai.03_auth")
C = importlib.import_module("src_rcai.01_config")
R = importlib.import_module("src_rcai.02_records")      # seal / unseal (the handbook's)
K = importlib.import_module("src_util_auth.codes")
HERE = Path(__file__).resolve().parent
APPROVED = HERE / "20_approved"
SEALED = HERE / "30_sealed" / "approved.bin"
LOCAL = HERE.parent / "dta" / "_1_processed" / "recruiter"
MOUNT = "/recruiter"
MAX_DAYS = 30
CODE_DAYS, MAX_FAILS, LOCK_MIN = 14, 5, 10
_FAILS = {}
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".pdf": "application/pdf",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}
GATE = b"""<!doctype html><html lang="en"><head><meta charset="utf-8"><link rel="icon" href="/favicon.ico?v=k1" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/03_img/favicon-32.png?v=k1"><link rel="apple-touch-icon" sizes="180x180" href="/03_img/apple-touch-icon.png?v=k1"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Private</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f0a17;color:#ece8f2;font:16px/1.5 Inter,system-ui,sans-serif}
main{max-width:30rem;width:100%%;box-sizing:border-box;padding:2rem 1.4rem;border-top:1px solid #f2cd57}h1{font-weight:600;font-size:1.4rem;margin:0 0 .5rem}p{color:#a79fb5;margin:0}
input{margin-top:1.2rem;width:100%%;box-sizing:border-box;padding:.8rem 1rem;background:#1a1226;color:#ece8f2;border:1px solid #3a2d4d;
font:500 1rem/1 Inter,system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase}input:focus{outline:none;border-color:#f2cd57}
button{margin-top:.8rem;padding:.7rem 1.2rem;background:#f2cd57;color:#0f0a17;border:0;font:600 .9rem Inter,system-ui,sans-serif;cursor:pointer}
.req{margin-top:2.4rem;padding-top:1.6rem;border-top:1px solid #2a2038}.req h2{font-weight:600;font-size:1.05rem;margin:0 0 .3rem}
.req input,.req select{text-transform:none;letter-spacing:0;margin-top:.7rem;width:100%%;box-sizing:border-box;padding:.75rem 1rem;background:#1a1226;color:#ece8f2;border:1px solid #3a2d4d;font:400 .95rem/1.2 Inter,system-ui,sans-serif}
.req select:focus{outline:none;border-color:#f2cd57}.req .hp{position:absolute;left:-9999px}.req button{width:100%%;padding:.9rem;font-size:.95rem}
.req .say{margin-top:.8rem;min-height:1.2em;color:#f2cd57}.req .say.bad{color:#ff8a8a}.req.done form{display:none}</style>
</head><body><main><h1>%s</h1><p>%s</p>%s</main></body></html>"""
FORM = b"""<form method="post" action="/recruiter/login" autocomplete="off"><input name="code" type="password" autocapitalize="characters"
aria-label="Code" placeholder="access code" maxlength="40" autofocus><button type="submit">Open</button></form>
<div class="req" id="req"><h2>No code yet?</h2><p>Tell me who you are and the role. The code comes to your email.</p>
<form id="rq" novalidate><input name="name" placeholder="Your name" autocomplete="name" maxlength="160" required>
<input name="email" type="email" placeholder="Work email" autocomplete="email" maxlength="160" required>
<input name="company" placeholder="Company hiring" autocomplete="organization" maxlength="160" required>
<input name="position" placeholder="Position you're hiring for" maxlength="160" required>
<input name="link" type="url" placeholder="Job posting link (optional)" maxlength="300">
<select name="timeline" aria-label="Hiring timeline"><option value="">When do you want to hire?</option><option>This month</option>
<option>Within 3 months</option><option>Later / pipeline</option></select>
<input class="hp" name="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
<button type="submit">Send the code to my email</button></form><p class="say" id="say" role="status"></p></div>
<script>(function(){var f=document.getElementById("rq"),s=document.getElementById("say");f.addEventListener("submit",function(e){e.preventDefault();
var d={};new FormData(f).forEach(function(v,k){d[k]=v});s.className="say";s.textContent="Sending...";
fetch("/r-cai/api/recruiter",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json().then(function(j){return[r.ok,j]})})
.then(function(x){if(x[0]){document.getElementById("req").classList.add("done");s.textContent="Got it. Your code comes by email within 24 hours."}
else{s.className="say bad";s.textContent=x[1].error||"That didn't go through. Try again."}}).catch(function(){s.className="say bad";s.textContent="That didn't go through. Try again."})})})()</script>"""


def _key():
    return hmac.new(A._secret(), b"role:recruiter:v2|" + K.fingerprint("recruiter"), hashlib.sha256).digest()


def _sign(body):
    return hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()


def _revoked():
    ids = {i.strip() for i in os.environ.get("RECRUITER_REVOKED", "").split(",") if i.strip()}
    f = LOCAL / "revoked.txt"
    if f.is_file():
        ids |= {l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    return ids


def _code_token():
    """The shared code's session: rec|code|exp|sig -- revocable like any link (RECRUITER_REVOKED=code)."""
    body = f"rec|code|{int(time.time() + CODE_DAYS * 86400)}"
    return f"{body}|{_sign(body)}"


def mint(label, days=14):
    """A new link for one recruiter. The ledger keeps id · label · dates (a pointer, never content)."""
    days = max(1, min(int(days), MAX_DAYS))
    rid, exp = secrets.token_hex(4), int(time.time() + days * 86400)
    body = f"rec|{rid}|{exp}"
    LOCAL.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[\t\n]", " ", label)[:80]
    with (LOCAL / "links.csv").open("a", encoding="utf-8") as f:
        f.write("\t".join([rid, name, time.strftime("%Y-%m-%d"), time.strftime("%Y-%m-%d", time.localtime(exp))]) + "\n")
    return rid, f"{MOUNT}/in/{body}|{_sign(body)}"


def valid(token):
    """The recruiter id, or None. Exactly rec|id|exp|sig, this role's key, not expired, not revoked."""
    if not K.ready("recruiter"):
        return None
    try:
        role, rid, exp, sig = (token or "").split("|")
        ok = role == "rec" and hmac.compare_digest(sig, _sign(f"{role}|{rid}|{exp}")) and int(exp) > time.time()
    except ValueError:
        return None
    return rid if ok and rid not in _revoked() else None


def _who(h):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    return valid(jar["yrec"].value) if "yrec" in jar else None


# -- the approved pages: a folder locally, one sealed blob hosted ---------------------------------------
def _pack():
    """{relpath: bytes} of 20_approved/, only the file types we serve, no dotfiles."""
    if not APPROVED.is_dir():
        return {}
    return {p.relative_to(APPROVED).as_posix(): p.read_bytes() for p in sorted(APPROVED.rglob("*"))
            if p.is_file() and p.suffix.lower() in TYPES and not any(s.startswith(".") for s in p.relative_to(APPROVED).parts)}


def seal_approved(key):
    """--bundle: 20_approved/ → 30_sealed/approved.bin. Re-sealed only when the content changed (no git churn)."""
    files = _pack()
    blob = json.dumps({k: base64.b64encode(v).decode() for k, v in files.items()}, sort_keys=True).encode()
    if SEALED.is_file() and R.unseal(SEALED.read_bytes(), key) == blob:
        return len(files), False
    SEALED.parent.mkdir(exist_ok=True)
    SEALED.write_bytes(R.seal(blob, key))
    return len(files), True


def _files():
    key = os.environ.get("RCAI_DOC_KEY", "")
    if os.environ.get("PORT") and key and SEALED.is_file():          # hosted
        try:
            return {k: base64.b64decode(v) for k, v in json.loads(R.unseal(SEALED.read_bytes(), key)).items()}
        except ValueError:
            return {}
    return {} if os.environ.get("PORT") else _pack()                  # hosted without the key: nothing, never raw


# -- http -------------------------------------------------------------------------------------------------
def _send(h, code, body, ctype="text/html; charset=utf-8", headers=()):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", "no-store")
    h.send_header("Referrer-Policy", "no-referrer")
    h.send_header("X-Robots-Tag", "noindex, nofollow")
    for k, v in headers:
        h.send_header(k, v)
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)
    return True


def _gate(h, code, title, line, form=False):
    return _send(h, code, GATE % (title.encode(), line.encode(), FORM if form else b""))


def _ip(h):
    fwd = h.headers.get("X-Forwarded-For", "") if os.environ.get("PORT") else ""
    return fwd.split(",")[0].strip() or h.client_address[0]


def _login(h):
    ip, now = _ip(h), time.time()
    _FAILS[ip] = [x for x in _FAILS.get(ip, []) if now - x < LOCK_MIN * 60]
    if len(_FAILS[ip]) >= MAX_FAILS:
        return _gate(h, 429, "Too many tries", "Wait a few minutes, then try again.")
    raw = h.rfile.read(min(int(h.headers.get("Content-Length", 0) or 0), 512)).decode("utf-8", "ignore")
    code = (parse_qs(raw).get("code") or [""])[0]
    if raw.lstrip().startswith("{"):
        try:
            code = str(json.loads(raw).get("code", ""))
        except (ValueError, AttributeError):
            code = ""
    if not K.check("recruiter", code):
        _FAILS[ip].append(now)
        return _gate(h, 401, "Wrong code", "Check the code you were sent.", form=True)
    if "code" in _revoked():
        return _gate(h, 401, "This code has closed", "Ask for a personal link.")
    tok = _code_token()
    return _send(h, 303, b"", headers=[("Location", MOUNT + "/"), ("Set-Cookie", _cookie(tok, CODE_DAYS * 86400))])


def _cookie(value, age):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"yrec={value}; Path={MOUNT}; Max-Age={age}; HttpOnly; SameSite=Lax{secure}"


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if path != MOUNT and not path.startswith(MOUNT + "/"):
        return False
    if method == "POST" and path == MOUNT + "/login":
        return _login(h)
    if method != "GET":
        return _gate(h, 405, "Not here", "This page only opens.")
    if path == MOUNT:
        return _send(h, 301, b"", headers=[("Location", MOUNT + "/")])
    rel = path[len(MOUNT) + 1:]
    if rel.startswith("in/"):
        token = rel[3:].replace("%7C", "|").replace("%7c", "|")
        if not valid(token):
            return _gate(h, 401, "This link has closed", "Links are personal and expire. Ask for a fresh one.")
        exp = int(token.split("|")[2])
        return _send(h, 303, b"", headers=[("Location", MOUNT + "/"), ("Set-Cookie", _cookie(token, max(0, exp - int(time.time()))))])
    if rel == "out":
        return _send(h, 303, b"", headers=[("Location", MOUNT + "/"), ("Set-Cookie", _cookie("", 0))])
    if not _who(h):
        return _gate(h, 401, "Recruiter access", "Enter your access code, or request one below.", form=True)
    files = _files()
    f = files.get(rel or "index.html")
    if f is None:
        if not files:
            return _gate(h, 200, "Nothing shared yet", "The pages for you are on their way.")
        return _gate(h, 404, "Not found", "That page is not part of what was shared.")
    return _send(h, 200, f, TYPES[Path(rel or "index.html").suffix.lower()])
