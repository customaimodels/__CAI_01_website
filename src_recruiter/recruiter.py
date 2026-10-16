"""RECRUITER, mounted at /recruiter (2026-10-16). One site, three policies:
    /behind-the-models/   public, indexable          (src_resume, via src_y_vault/vault.py public=True)
    /recruiter/           a recruiter's own link     (this file)
    /y-vault/             the owner's PIN            (src_y_vault/vault.py)

GET /recruiter/in/<token>   a link he minted (run.py --recruiter-link): sets the yrec cookie (Path=/recruiter) → /recruiter/
GET /recruiter/...          the APPROVED pages only (signed in); everything else 401
GET /recruiter/out          clears the cookie

Tokens: rec|<id>|<expiry>|sig, signed with a key derived from RCAI_SECRET for this role alone -- it never verifies
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

A = importlib.import_module("src_rcai.03_auth")
R = importlib.import_module("src_rcai.02_records")      # seal / unseal (the handbook's)
HERE = Path(__file__).resolve().parent
APPROVED = HERE / "20_approved"
SEALED = HERE / "30_sealed" / "approved.bin"
LOCAL = HERE.parent / "dta" / "_1_processed" / "recruiter"
MOUNT = "/recruiter"
MAX_DAYS = 30
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".pdf": "application/pdf",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}
GATE = b"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Private</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f0a17;color:#ece8f2;font:16px/1.5 Inter,system-ui,sans-serif}
main{max-width:30rem;padding:2rem;border-top:1px solid #f2cd57}h1{font-weight:600;font-size:1.4rem;margin:0 0 .5rem}p{color:#a79fb5;margin:0}</style>
</head><body><main><h1>%s</h1><p>%s</p></main></body></html>"""


def _key():
    return hmac.new(A._secret(), b"role:recruiter:v1", hashlib.sha256).digest()


def _sign(body):
    return hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()


def _revoked():
    ids = {i.strip() for i in os.environ.get("RECRUITER_REVOKED", "").split(",") if i.strip()}
    f = LOCAL / "revoked.txt"
    if f.is_file():
        ids |= {l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    return ids


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


def _gate(h, code, title, line):
    return _send(h, code, GATE % (title.encode(), line.encode()))


def _cookie(value, age):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"yrec={value}; Path={MOUNT}; Max-Age={age}; HttpOnly; SameSite=Lax{secure}"


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if path != MOUNT and not path.startswith(MOUNT + "/"):
        return False
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
        return _gate(h, 401, "Private", "This page opens from the link you were sent.")
    files = _files()
    f = files.get(rel or "index.html")
    if f is None:
        if not files:
            return _gate(h, 200, "Nothing shared yet", "The pages for you are on their way.")
        return _gate(h, 404, "Not found", "That page is not part of what was shared.")
    return _send(h, 200, f, TYPES[Path(rel or "index.html").suffix.lower()])
