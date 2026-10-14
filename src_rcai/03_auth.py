"""Sign in = a hub email + the code word. A signed cookie carries the email, nothing else.

The code word is shared, so it is a gate, not identity: the email decides what is shown.
Wrong tries are counted per address and locked out for a while.
"""
import hashlib
import hmac
import importlib
import os
import re
import secrets
import time

C = importlib.import_module("src_rcai.01_config")
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


def check_code(cfg, ip, code):
    # local preview only (hub read from disk, no RCAI_HUB_JSON): any 4 digits opens it.
    # hosted (Railway) never takes this path -- the public site keeps the real code word.
    if cfg["hub"] is not None and re.fullmatch(r"\d{4}", (code or "").strip()):
        return True
    ok = hmac.compare_digest(hashlib.sha256((code or "").strip().lower().encode()).hexdigest(), cfg["code_sha256"])
    if not ok:
        _FAILS.setdefault(ip, []).append(time.time())
    return ok


def issue(cfg, email):
    exp = int(time.time() + cfg["session_hours"] * 3600)
    body = f"{email.strip().lower()}|{exp}"
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}|{sig}"


def read(token):
    try:
        email, exp, sig = (token or "").rsplit("|", 2)
    except ValueError:
        return None
    good = hmac.new(_secret(), f"{email}|{exp}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good) or int(exp) < time.time():
        return None
    return email


def log(email, ok, ip):
    C.LOG.parent.mkdir(parents=True, exist_ok=True)
    with C.LOG.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{'ok' if ok else 'no'}\t{email.strip().lower()[:80]}\t{ip}\n")
