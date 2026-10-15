"""Sign in = a hub email + its password. A signed cookie carries the email and its password version.

No own password yet (05_users) = the shared code word opens, and the email decides what is shown.
Own password set = only the newest one opens; changing it bumps the version, so every older cookie dies.
Wrong tries are counted per address and locked out for a while.
RCAI_REQUIRE_OWN=1 (hosted): an email without its own password is refused -- the shared code and the local
4-digit door are both shut. Unset it and the shared code is back after one restart (the rollback).
The same gate ends every shared-code (v0) session, so no secret rotation is needed for it.
RCAI_SECRET signs this cookie AND the _Y_VAULT cookie (src_y_vault/vault.py): rotating it ends both.
"""
import hashlib
import hmac
import importlib
import os
import re
import secrets
import time

C = importlib.import_module("src_rcai.01_config")
U = importlib.import_module("src_rcai.05_users")
_FAILS = {}  # ip -> [timestamps]


def _secret():
    if os.environ.get("RCAI_SECRET"):
        return os.environ["RCAI_SECRET"].encode()
    if not C.SECRET.exists():
        C.SECRET.parent.mkdir(parents=True, exist_ok=True)
        C.SECRET.write_text(secrets.token_hex(32))
        C.SECRET.chmod(0o600)
    return C.SECRET.read_text().strip().encode()


def locked(cfg, ip):
    now = time.time()
    hits = [t for t in _FAILS.get(ip, []) if now - t < cfg["lockout_minutes"] * 60]
    _FAILS[ip] = hits
    return len(hits) >= cfg["max_fails"]


def fail(ip):
    _FAILS.setdefault(ip, []).append(time.time())


def require_own():
    return os.environ.get("RCAI_REQUIRE_OWN") == "1"


def check_code(cfg, ip, code, email=""):
    own = U.check(email, code or "")              # own password set: only the newest opens, nothing else
    if own is not None:
        if not own:
            fail(ip)
        return own
    if require_own():                             # no own password = no way in; never falls back to the shared code
        fail(ip)
        return False
    # local preview only (hub read from disk, no RCAI_HUB_JSON): any 4 digits opens an email with no own password.
    # hosted (Railway) never takes this path -- the public site keeps the real code word.
    if cfg["hub"] is not None and re.fullmatch(r"\d{4}", (code or "").strip()):
        return True
    ok = hmac.compare_digest(hashlib.sha256((code or "").strip().lower().encode()).hexdigest(), cfg["code_sha256"])
    if not ok:
        fail(ip)
    return ok


def issue(cfg, email):
    email = email.strip().lower()
    exp = int(time.time() + cfg["session_hours"] * 3600)
    body = f"{email}|{U.version(email)}|{exp}"
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}|{sig}"


def read(token):
    try:
        email, ver, exp, sig = (token or "").rsplit("|", 3)
    except ValueError:
        return None
    good = hmac.new(_secret(), f"{email}|{ver}|{exp}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good) or int(exp) < time.time() or ver != str(U.version(email)):
        return None
    if ver == "0" and require_own():              # every shared-code session ends the moment the gate closes
        return None
    return email


def log(email, ok, ip, what="login"):
    C.LOG.parent.mkdir(parents=True, exist_ok=True)
    with C.LOG.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{'ok' if ok else 'no'}\t{email.strip().lower()[:80]}\t{ip}\t{what}\n")
