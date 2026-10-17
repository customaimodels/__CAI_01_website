"""The owner and recruiter code words (rotated 2026-10-16, after the sha256 hashes were found in the public repo).

Stored ONLY as PBKDF2-SHA256 hashes (600k rounds, own salt; stdlib on every Python -- scrypt is missing on some), never in git:
    hosted  Railway variables YVAULT_CODE_HASH · RECRUITER_CODE_HASH
    local   dta/_1_processed/auth/hashes.json (never bundled; written by run.py --rotate-codes)
A variable that is SET wins, even when empty. Missing, empty or malformed = every login refused (fail closed).
Old bare sha256 hashes are never accepted: HELLO / HELLOCAI and anything before them are dead.

The hash also feeds the session keys (fingerprint): rotating a code ends every session signed under the old one.
Never log or print a code, a hash or a variable value.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "dta" / "_1_processed" / "auth"
HASHES = LOCAL / "hashes.json"
VARS = {"owner": "YVAULT_CODE_HASH", "recruiter": "RECRUITER_CODE_HASH"}
ALGO, ROUNDS, DK = "pbkdf2_sha256", 600_000, 32
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"      # no 0/O, 1/I/L: read aloud, typed once


def normalize(code):
    """Case-blind; spaces and dashes don't count (K7QP-M3XW… = k7qpm3xw…)."""
    return "".join(c for c in str(code or "").upper() if c.isalnum())[:64]


def make(code):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", normalize(code).encode(), salt, ROUNDS, DK)
    b = lambda x: base64.b64encode(x).decode()
    return f"{ALGO}${ROUNDS}${b(salt)}${b(dk)}"


def _parse(stored):
    try:
        kind, rounds, salt, dk = (stored or "").split("$")
        rounds = int(rounds)
        salt, dk = base64.b64decode(salt, validate=True), base64.b64decode(dk, validate=True)
    except ValueError:
        return None
    if kind != ALGO or rounds < 300_000 or len(salt) < 16 or len(dk) < 32:
        return None
    return rounds, salt, dk


def stored(role):
    """The hash for 'owner' or 'recruiter', or "" (= refuse)."""
    var = VARS[role]
    if var in os.environ:
        return os.environ[var].strip()
    if os.environ.get("PORT"):                     # hosted: the variable or nothing
        return ""
    try:
        return str(json.loads(HASHES.read_text(encoding="utf-8")).get(var, "")).strip()
    except (OSError, ValueError):
        return ""


def check(role, code):
    parsed = _parse(stored(role))
    word = normalize(code)
    if not parsed or len(word) < 12:              # no hash, bad hash, or a short guess: no
        return False
    rounds, salt, dk = parsed
    got = hashlib.pbkdf2_hmac("sha256", word.encode(), salt, rounds, len(dk))
    return hmac.compare_digest(got, dk)


def ready(role):
    return _parse(stored(role)) is not None


def fingerprint(role):
    """Binds sessions to the current hash. b"" when there is none (callers refuse anyway)."""
    s = stored(role)
    return hashlib.sha256(s.encode()).hexdigest()[:24].encode() if _parse(s) else b""


def new_code():
    """16 characters from a 31-letter alphabet, in four groups (~79 bits)."""
    raw = "".join(secrets.choice(ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def rotate():
    """New owner + recruiter codes. Writes three 0600 files under dta/_1_processed/auth/, prints nothing secret.
    Returns the paths."""
    LOCAL.mkdir(parents=True, exist_ok=True)
    codes = {"owner": new_code(), "recruiter": new_code()}
    while codes["owner"] == codes["recruiter"]:
        codes["recruiter"] = new_code()
    hashes = {VARS[k]: make(v) for k, v in codes.items()}
    out = {
        HASHES: json.dumps(hashes, indent=2) + "\n",
        LOCAL / "railway.env": "".join(f"{k}={v}\n" for k, v in hashes.items()),
        LOCAL / "NEW_CODES.txt": ("# Move both into your password manager, then ERASE this file.\n"
                                  f"owner vault  /y-vault/    {codes['owner']}\n"
                                  f"recruiters   /recruiter/  {codes['recruiter']}\n"),
    }
    for f, text in out.items():
        f.write_text(text, encoding="utf-8")
        f.chmod(0o600)
    return list(out)
