"""Sign up with Google or Microsoft (2026-10-18). Stdlib only: OpenID Connect, code flow + PKCE + nonce.

    GET /r-cai/api/oauth/<google|microsoft>/start     → 302 to the provider, a signed state cookie (rcai_oa)
    GET /r-cai/api/oauth/<google|microsoft>/callback  → code swapped server-side, id_token claims checked,
                                                        a 30-min identity cookie (rcai_id), 302 to /r-cai/#signup
    GET /r-cai/api/oauth/me                           → {on: {google, microsoft}, id: {name, email, provider} | null}

What it never does: open a hub. A provider only proves WHO someone is; what they may see stays in the Clients Hub.
- An email the hub already knows (John, Cory, Schuggies) or an owner → refused here; they keep email + code word.
- A new email → the signup face, prefilled and locked to that email; /api/signup then files it in 08_inbox.
Keys: RCAI_GOOGLE_ID · RCAI_GOOGLE_SECRET · RCAI_MS_ID · RCAI_MS_SECRET (Railway), or locally
dta/_1_processed/auth/oauth.json {"google": {"id","secret"}, "microsoft": {...}} (gitignored, never bundled).
A provider without both keys = its button greys out and /start answers 503. Fail closed.
Redirect URI to register: <base>/r-cai/api/oauth/<provider>/callback, base = RCAI_BASE_URL (hosted:
https://customaimodels.com) or, locally only, http://localhost:<port>.
The id_token comes straight from the token endpoint over TLS, so its claims are trusted without a JWKS check
(OpenID Connect Core 3.1.3.7); iss · aud · exp · nonce are still checked.
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
import urllib.parse
import urllib.request

C = importlib.import_module("src_rcai.01_config")
A = importlib.import_module("src_rcai.03_auth")
R = importlib.import_module("src_rcai.02_records")

KEYS = C.PROC / "auth" / "oauth.json"
ID_MIN = 30
PROVIDERS = {
    "google": {"auth": "https://accounts.google.com/o/oauth2/v2/auth",
               "token": "https://oauth2.googleapis.com/token",
               "env": ("RCAI_GOOGLE_ID", "RCAI_GOOGLE_SECRET"),
               "iss": lambda iss, c: iss in ("https://accounts.google.com", "accounts.google.com")},
    "microsoft": {"auth": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                  "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                  "env": ("RCAI_MS_ID", "RCAI_MS_SECRET"),
                  "iss": lambda iss, c: bool(c.get("tid")) and iss == f"https://login.microsoftonline.com/{c['tid']}/v2.0"},
}
POST = urllib.request.urlopen   # tests swap this for a fake token endpoint


def keys(name):
    p = PROVIDERS[name]
    cid, sec = (os.environ.get(k, "") for k in p["env"])
    if not (cid and sec) and KEYS.exists():
        try:
            k = json.loads(KEYS.read_text()).get(name) or {}
            cid, sec = k.get("id", ""), k.get("secret", "")
        except (ValueError, AttributeError):
            cid = sec = ""
    return (cid, sec) if cid and sec else None


def on():
    return {n: keys(n) is not None for n in PROVIDERS}


def base(h):
    if os.environ.get("RCAI_BASE_URL"):
        return os.environ["RCAI_BASE_URL"].rstrip("/")
    host = h.headers.get("Host", "")
    if os.environ.get("PORT") or not re.fullmatch(r"(localhost|127\.0\.0\.1)(:\d+)?", host):
        return None                                  # hosted without RCAI_BASE_URL, or a foreign Host: refuse
    return f"http://{host}"


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _sign(body):
    """Cookie-safe: base64url(body).hmac -- a name with a space or an accent would break a raw cookie."""
    return f"{_b64(body.encode())}.{hmac.new(A._secret(), (b'rcai-oauth|' + body.encode()), hashlib.sha256).hexdigest()}"


def _open(token, parts):
    try:
        raw, sig = (token or "").rsplit(".", 1)
        body = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    good = hmac.new(A._secret(), b"rcai-oauth|" + body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good):
        return None
    f = body.split("|")
    if len(f) != parts or not f[-1].isdigit() or int(f[-1]) < time.time():
        return None
    return f


def start(h, name):
    """→ (url, state cookie value) or None (provider off / no base)."""
    k, b = keys(name), base(h)
    if not k or not b:
        return None
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    q = {"client_id": k[0], "response_type": "code", "scope": "openid email profile",
         "redirect_uri": f"{b}{C.MOUNT}/api/oauth/{name}/callback", "state": state, "nonce": nonce,
         "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256",
         "prompt": "select_account"}
    return f"{PROVIDERS[name]['auth']}?{urllib.parse.urlencode(q)}", _sign(f"{name}|{state}|{nonce}|{verifier}|{int(time.time()) + 600}")


def _claims(id_token):
    try:
        seg = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))
    except (IndexError, ValueError):
        return None


def callback(h, name, query, state_cookie, cfg):
    """→ (identity cookie value, None) or (None, reason). Never opens a hub."""
    f = _open(state_cookie, 5)
    q = urllib.parse.parse_qs(query)
    if not f or f[0] != name or not hmac.compare_digest(f[1], (q.get("state") or [""])[0]):
        return None, "That sign-in expired. Try again."
    if q.get("error") or not q.get("code"):
        return None, "Sign-in was cancelled."
    k, b = keys(name), base(h)
    if not k or not b:
        return None, "That sign-in is not switched on yet."
    form = urllib.parse.urlencode({"grant_type": "authorization_code", "code": q["code"][0], "client_id": k[0],
                                   "client_secret": k[1], "redirect_uri": f"{b}{C.MOUNT}/api/oauth/{name}/callback",
                                   "code_verifier": f[3]}).encode()
    try:
        req = urllib.request.Request(PROVIDERS[name]["token"], data=form, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        with POST(req, timeout=10) as r:
            tok = json.loads(r.read())
    except Exception:
        return None, "Couldn't reach the sign-in service. Try again."
    c = _claims(tok.get("id_token", ""))
    if not c or c.get("aud") != k[0] or not PROVIDERS[name]["iss"](c.get("iss", ""), c) \
            or int(c.get("exp", 0)) < time.time() or not hmac.compare_digest(str(c.get("nonce", "")), f[2]):
        return None, "That sign-in didn't check out. Try again."
    email = (c.get("email") or (c.get("preferred_username") if name == "microsoft" else "") or "").strip().lower()
    if name == "google" and c.get("email_verified") is not True:
        return None, "That Google account has no verified email."
    if not re.fullmatch(r"[^@\s|]+@[^@\s|]+\.[^@\s|]+", email):
        return None, "That account has no email we can use."
    if email in cfg["owners"] or R.person_by_email(R.load(cfg), email):
        return None, "You already have a hub. Sign in with your email and access code."
    name_ = re.sub(r"[|\r\n]", " ", str(c.get("name") or email.split("@")[0]))[:80].strip()
    return _sign(f"{email}|{name_}|{name}|{int(time.time()) + ID_MIN * 60}"), None


def identity(token):
    f = _open(token, 4)
    return {"email": f[0], "name": f[1], "provider": f[2]} if f else None
