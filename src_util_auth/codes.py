"""The owner and recruiter passphrases (rotated 2026-10-16 after the sha256 hashes were found in the public repo;
same day he chose his own: one permanent, memorable passphrase per door, reusable, no expiry -- run.py --set-codes).

Stored ONLY as PBKDF2-SHA256 hashes (600k rounds, own salt; stdlib on every Python -- scrypt is missing on some), never in git:
    hosted  Railway variables YVAULT_CODE_HASH · RECRUITER_CODE_HASH
    local   dta/_1_processed/auth/hashes.json (never bundled; written by run.py --rotate-codes)
A variable that is SET wins, even when empty. Missing, empty or malformed = every login refused (fail closed).
Old bare sha256 hashes are never accepted: HELLO / HELLOCAI and anything before them are dead.
Short passphrases are safe only because the hash never ships and each door locks an IP after a few wrong tries.

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
LEAK = LOCAL / "leak.json"
VARS = {"owner": "YVAULT_CODE_HASH", "recruiter": "RECRUITER_CODE_HASH"}
ALGO, ROUNDS, DK = "pbkdf2_sha256", 600_000, 32
MIN = 6                                            # his own passphrases; below this = refused
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
    if not parsed or len(word) < MIN:              # no hash, bad hash, or a short guess: no
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


def set_codes(owner, recruiter):
    """His own passphrases. Writes hashes.json + railway.env + leak.json (sha256 of each word, so --bundle can refuse
    to ship them), all 0600, and removes the dead NEW_CODES.txt. Prints nothing secret. Raises ValueError when unusable."""
    o, r = normalize(owner), normalize(recruiter)
    if len(o) < MIN or len(r) < MIN:
        raise ValueError(f"each passphrase needs {MIN}+ letters or digits")
    if o == r:
        raise ValueError("owner and recruiter passphrases must differ")
    LOCAL.mkdir(parents=True, exist_ok=True)
    hashes = {VARS["owner"]: make(o), VARS["recruiter"]: make(r)}
    out = {
        HASHES: json.dumps(hashes, indent=2) + "\n",
        LOCAL / "railway.env": "".join(f"{k}={v}\n" for k, v in hashes.items()),
        LEAK: json.dumps([hashlib.sha256(w.encode()).hexdigest() for w in (o, r)]) + "\n",
    }
    for f, text in out.items():
        f.write_text(text, encoding="utf-8")
        f.chmod(0o600)
    (LOCAL / "NEW_CODES.txt").unlink(missing_ok=True)       # the random codes it held are dead the moment this runs
    return list(out)


def leaked(text):
    """True when any word in text is one of the current passphrases (compared by sha256, never by the word)."""
    try:
        bad = set(json.loads(LEAK.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return False
    import re
    return any(hashlib.sha256(w.upper().encode()).hexdigest() in bad for w in set(re.findall(r"[A-Za-z0-9]{%d,64}" % MIN, text)))
