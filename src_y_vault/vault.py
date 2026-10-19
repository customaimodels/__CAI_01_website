"""_Y_VAULT, mounted at /y-vault on whatever server carries the site (run.py locally, main.py on Railway).

    handle(h, "GET"|"POST") -> True if the request was /y-vault/..., answered here; False = not ours.

GET  /y-vault/              the gate + GOAL INDICATORS (10_web/index.html; "the shelf" until 2026-10-18)
POST /y-vault/api/login     {pin}  → sets the yvault cookie (Path=/y-vault)
GET  /y-vault/api/list      GOAL INDICATORS: guides + resume on top, the managers below (signed in only)
                            The guides' source is __ss3_mketing/src_blt/guides; sync_from_mketing.py pulls them in here.
GET  /y-vault/<page>.html   one page (signed in only)
GET  /y-vault/resume/...    the resume site, ../src_resume served as is (signed in only)
GET  /y-vault/ydta/<file>   one file of _0ds_CAI/__Ydta, read only (signed in + LOCAL only; hosted = 404)
POST /y-vault/api/logout
GET  /behind-the-models/... the same resume site, PUBLIC (the landing's "About the owner's work and portfolio")

The code (rotated 2026-10-16): a PBKDF2 hash in the Railway variable YVAULT_CODE_HASH, never in git (src_util_auth/codes.py).
No hash = no login. The shelf pages (*.html here) never ship readable: --bundle seals them into 30_sealed/shelf.bin
(key = RCAI_DOC_KEY); hosted without the key, the shelf is empty.
"""
import hashlib
import hmac
import importlib
import json
import os
import re
import base64
import time
from http.cookies import SimpleCookie
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
A = importlib.import_module("src_rcai.03_auth")      # same cookie secret as R-CAI, its own derived key
K = importlib.import_module("src_util_auth.codes")
R = importlib.import_module("src_rcai.02_records")   # seal / unseal (the handbook's)
HERE = Path(__file__).resolve().parent
WEB = HERE / "10_web"
SEALED = HERE / "30_sealed" / "shelf.bin"
RESUME = HERE.parent / "src_resume"                 # his resume site, never edited here
YDTA = HERE.parents[1] / "__Ydta"                   # his command data: READ here (local only), written only by _0ds_CAI/run.py ydta
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".pdf": "application/pdf",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}
MOUNT = "/y-vault"
OWNER = "/behind-the-models"                        # public face of src_resume, linked from the landing footer (2026-10-14)
HOURS, MAX_FAILS, LOCK_MIN = 12, 5, 10
_FAILS = {}
TITLE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def _local_shelf():
    return {f.name: f.read_bytes() for f in sorted(HERE.glob("*.html"))}


def seal_shelf(key):
    """--bundle: the shelf pages → 30_sealed/shelf.bin. Re-sealed only when they changed (no git churn)."""
    files = _local_shelf()
    blob = json.dumps({k: base64.b64encode(v).decode() for k, v in files.items()}, sort_keys=True).encode()
    if SEALED.is_file() and R.unseal(SEALED.read_bytes(), key) == blob:
        return len(files), False
    SEALED.parent.mkdir(exist_ok=True)
    SEALED.write_bytes(R.seal(blob, key))
    return len(files), True


def _shelf():
    """{name: bytes}. Local = the files; hosted = the sealed blob, or nothing (never raw)."""
    if not os.environ.get("PORT"):
        return _local_shelf()
    key = os.environ.get("RCAI_DOC_KEY", "")
    if not (key and SEALED.is_file()):
        return {}
    try:
        return {k: base64.b64decode(v) for k, v in json.loads(R.unseal(SEALED.read_bytes(), key)).items()}
    except ValueError:
        return {}


def ydta_files():
    """__Ydta, his command data (written ONLY by `_0ds_CAI/run.py ydta add`). Read here, never written. Local only."""
    if os.environ.get("PORT") or not YDTA.is_dir():
        return []
    return [p.name for p in sorted(YDTA.iterdir())
            if p.is_file() and not p.name.startswith((".", "_LOG")) and p.suffix.lower() in TYPES]


def pages():
    """GOAL INDICATORS: EIGHT SQUARES since 2026-10-19 (his word), two rows of four, every entry group "square":
    row "company" = the sections that keep CAI alive, ss3 → ss6:
      marketing  MARKETING STUDIO (ss3, local app). The LinkedIn + CAI Content guides ride INSIDE it ("inside"),
                 so they still open on the hosted vault, where the app itself does not exist.
      business   BUSINESS STUDIO (ss4, local app)
      users      USERS STUDIO (ss5, PROPOSAL, later)
      aut        AUTOMATIONS (ss6, src_aut0run: watches __ss6_aut, never runs)
    row "brain" = the yellow layer across every section:
      scrn       SCRN · utility (the Y in the browser; PROPOSAL -- shows SCRN alive/off, opens nothing yet)
      cli        CLI · utility (__vCLI; empty for now)
      ydta       Ydta (his command data; the master resume first -- it replaced the resume square)
      ysrc       Ysrc (the back door when SCRN breaks: _0ds_CAI/run.py; tap = the run line on the clipboard)
    local=False on the hosted vault: the square shows dimmed, and only its "inside" links work."""
    local = not os.environ.get("PORT")
    inside = []
    for name, raw in _shelf().items():
        t = TITLE.search(raw[:4000].decode("utf-8", "ignore"))
        title = t.group(1).strip() if t else Path(name).stem.strip("_")
        inside.append({"file": name, "title": "LinkedIn" if "linked" in name.lower() else title.split(" · ")[0]})
    ydta = [{"file": "ydta/" + n, "title": "Master resume" if "resume" in n.lower() else Path(n).stem.strip("_")[:18]}
            for n in ydta_files()]
    sq = lambda row, **k: {"group": "square", "row": row, **k}
    return [sq("company", file="marketing", title="Marketing Studio", kind="marketing", ss="ss3",
               line="Say it once, post it everywhere.", inside=inside,
               local=local and (HERE.parent / "src_y_studio").is_dir()),
            sq("company", file="business", title="Business Studio", kind="business", ss="ss4",
               line="Legal, money, offers, partners.", local=local and (HERE.parent / "src_y_business").is_dir()),
            sq("company", file="", title="Users Studio", kind="users", ss="ss5", line="Later.", soon=True, local=local),
            sq("company", file="aut0run", title="Automations", kind="aut", ss="ss6",
               line="The loops that keep CAI alive.", local=local and (HERE.parent / "src_aut0run").is_dir()),
            sq("brain", file="", title="SCRN · utility", kind="scrn", line="The Y, in the browser. Next.", soon=True,
               local=local),
            sq("brain", file="", title="CLI · utility", kind="cli", line="Empty for now.", soon=True, local=local),
            sq("brain", file="", title="Ydta", kind="ydta", line="His command data.", inside=ydta, local=local,
               open=False),
            sq("brain", file="", title="Ysrc", kind="ysrc", line="SCRN down? cd ~/_0ds_CAI · python3 run.py",
               copy="cd ~/_0ds_CAI && python3 run.py", local=True)]


def _resume(h, rel, public=False):
    """/y-vault/resume/<file> or /behind-the-models/<file>: a file inside src_resume, never outside it, never NOTE.md.
    public=True ONLY from the OWNER branch of handle(): same bytes, indexable. Everything else stays private."""
    sub = rel.split("/", 1)[1] if "/" in rel else ""
    sub = sub or "index.html"
    f = (RESUME / sub).resolve()
    if RESUME.resolve() not in f.parents or not f.is_file() or f.suffix.lower() not in TYPES:
        return _json(h, 404, {"error": "not found"})
    return _send(h, 200, f.read_bytes(), TYPES[f.suffix.lower()], public=public)


def _send(h, code, body, ctype, cookie=None, public=False):
    """Private by default: every vault answer carries noindex, nofollow. Only /behind-the-models/ files pass public=True."""
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", "no-store")
    h.send_header("Referrer-Policy", "no-referrer")
    if not public:
        h.send_header("X-Robots-Tag", "noindex, nofollow")
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


def _key():
    """The owner's own signing key, derived from RCAI_SECRET + the current code hash. A token signed for R-CAI or
    /recruiter never verifies here (2026-10-16: an R-CAI cookie replayed as yvault opened the vault), and rotating
    the code ends every vault session (v2, 2026-10-16)."""
    return hmac.new(A._secret(), b"role:owner-vault:v2|" + K.fingerprint("owner"), hashlib.sha256).digest()


def _issue():
    body = f"vault|{int(time.time() + HOURS * 3600)}"
    return f"{body}|{hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()}"


def _in(h):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    if not K.ready("owner"):
        return False
    try:
        who, exp, sig = jar["yvault"].value.split("|")
        good = hmac.new(_key(), f"{who}|{exp}".encode(), hashlib.sha256).hexdigest()
        return who == "vault" and hmac.compare_digest(sig, good) and int(exp) > time.time()
    except (KeyError, ValueError):
        return False


def _locked(ip):
    if ip in ("127.0.0.1", "::1") and not os.environ.get("PORT"):   # his own Mac, local preview: never locks him out
        return False
    now = time.time()
    _FAILS[ip] = [t for t in _FAILS.get(ip, []) if now - t < LOCK_MIN * 60]
    return len(_FAILS[ip]) >= MAX_FAILS


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if method == "GET" and (path == OWNER or path.startswith(OWNER + "/")):
        if path == OWNER:
            h.send_response(301)
            h.send_header("Location", OWNER + "/")
            h.send_header("Content-Length", "0")
            h.end_headers()
            return True
        return _resume(h, path[1:], public=True)
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
        if rel == "resume":
            h.send_response(301)
            h.send_header("Location", MOUNT + "/resume/")
            h.send_header("Content-Length", "0")
            h.end_headers()
            return True
        if rel.startswith("resume/"):
            return _resume(h, rel)
        if rel.startswith("ydta/"):                    # local only: ydta_files() is empty on a hosted server
            name = rel[5:]
            if name not in ydta_files():
                return _json(h, 404, {"error": "not found"})
            return _send(h, 200, (YDTA / name).read_bytes(), TYPES[Path(name).suffix.lower()])
        shelf = _shelf()
        if rel in shelf:
            return _send(h, 200, shelf[rel], "text/html; charset=utf-8")
        return _json(h, 404, {"error": "not found"})
    if rel == "api/logout":
        return _json(h, 200, {"in": False}, _cookie("", 0))
    if rel != "api/login":
        return _json(h, 404, {"error": "not found"})
    ip = _ip(h)
    if _locked(ip):
        return _json(h, 429, {"error": "Too many tries. Wait a few minutes."})
    try:
        pin = str(json.loads(h.rfile.read(min(int(h.headers.get("Content-Length", 0) or 0), 512)) or b"{}").get("pin", ""))
    except (ValueError, AttributeError):
        return _json(h, 400, {"error": "bad request"})
    if not K.check("owner", pin):
        _FAILS.setdefault(ip, []).append(time.time())
        return _json(h, 401, {"error": "Wrong code."})
    return _json(h, 200, {"in": True}, _cookie(_issue(), HOURS * 3600))
