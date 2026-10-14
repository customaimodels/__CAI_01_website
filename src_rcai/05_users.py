"""Who has their own password, and every password they ever set: ONE file, users.csv.

    email, pw_1, pw_1_set, pw_2, pw_2_set, ...     a change never overwrites: it adds the next pair of columns.

Only salted pbkdf2 hashes are stored, never a password. No own password yet = the shared code word still opens.
Where it lives: RCAI_DATA_DIR if set (Railway: a volume), else dta/_1_processed/rcai locally.
Hosted with no RCAI_DATA_DIR = changes are OFF (a container's disk forgets on every deploy: a password
that silently reverts is worse than none). Never in git, never in the bundle.

The MASTER table (master()) joins it with the hub records: one row per person × project, user info,
where the project lives, and the date each password was set (never the hash).
"""
import csv
import hashlib
import hmac
import importlib
import io
import os
import secrets
import time
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
ITER = 200_000
MIN_LEN = 8


def store():
    """The folder that holds users.csv, or None when changes are off (hosted without a volume)."""
    if os.environ.get("RCAI_DATA_DIR"):
        return Path(os.environ["RCAI_DATA_DIR"])
    if os.environ.get("RCAI_HUB_JSON"):
        return None
    return C.PROC / "rcai"


def _file():
    s = store()
    return s / "users.csv" if s else None


def load():
    """email -> [(hash, set_at), ...] oldest first."""
    f = _file()
    if not f or not f.exists():
        return {}
    out = {}
    with f.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pws, n = [], 1
            while row.get(f"pw_{n}"):
                pws.append((row[f"pw_{n}"], row.get(f"pw_{n}_set", "")))
                n += 1
            out[row["email"].strip().lower()] = pws
    return out


def _save(db):
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    width = max([len(v) for v in db.values()] + [1])
    head = ["email"] + [c for n in range(1, width + 1) for c in (f"pw_{n}", f"pw_{n}_set")]
    tmp = f.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for email, pws in sorted(db.items()):
            w.writerow([email] + [x for pw in pws for x in pw] + [""] * (2 * (width - len(pws))))
    tmp.chmod(0o600)
    tmp.replace(f)


def _hash(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), ITER).hex()
    return f"pbkdf2${ITER}${salt}${h}"


def _match(pw, stored):
    try:
        _, it, salt, h = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex()
    except ValueError:
        return False
    return hmac.compare_digest(got, h)


def version(email):
    """How many passwords this email has set. 0 = still on the shared code word. Rides in the cookie."""
    return len(load().get((email or "").strip().lower(), []))


def has_own(email):
    return version(email) > 0


def check(email, pw):
    """True/False when the email has its own password (only the newest opens); None = no own password."""
    pws = load().get((email or "").strip().lower())
    return _match(pw, pws[-1][0]) if pws else None


def change(email, new):
    """Adds the next pw_N column for this email. Returns the new version number."""
    email = email.strip().lower()
    db = load()
    db.setdefault(email, []).append((_hash(new), time.strftime("%Y-%m-%d %H:%M")))
    _save(db)
    return len(db[email])


def problem(new, current=""):
    """Why a new password is refused, or None."""
    if len(new) < MIN_LEN:
        return f"At least {MIN_LEN} characters."
    if len(new) > 128:
        return "128 characters at most."
    if new == current:
        return "Pick a password you haven't just used."
    return None


# -- the master table ------------------------------------------------------------------------------
def master(cfg):
    """One row per person × project: who they are, what they see, where it lives, when each password was set."""
    R = importlib.import_module("src_rcai.02_records")
    db, pws = R.load(cfg), load()
    rows = []
    people = list(db["people"].values()) + [{"id": "owner", "name": "Owner", "email": e, "role": "Owner",
                                             "company": "", "hub": True} for e in cfg["owners"]]
    for p in people:
        email = (p.get("email") or "").lower()
        company = db["companies"].get(p.get("company"), {}).get("name", "Custom AI Models" if p["id"] == "owner" else "")
        sees = list(db["projects"]) if p["id"] == "owner" else db["access"].get(p["id"], [])
        user = {"user_id": p["id"], "client_id": p.get("client_id", ""), "name": p.get("name", ""), "email": email,
                "role": p.get("role", ""), "company": company, "hub": "yes" if p.get("hub") else "no",
                "password": f"own · v{len(pws[email])}" if pws.get(email) else "shared code word"}
        for n, (_, at) in enumerate(pws.get(email, []), 1):
            user[f"pw_{n}_set"] = at
        for pid in sees or [None]:
            pr = db["projects"].get(pid, {}) if pid else {}
            d = db.get("delivery", {}).get(pid, {}) if pid else {}
            rows.append({**user, "project_id": pid or "", "project": pr.get("name", ""), "status": pr.get("status", ""),
                         "live": d.get("live") or cfg["links"].get(pid, "") if pid else "",
                         "git": d.get("git", ""), "railway": d.get("railway", ""), "account_email": d.get("email", ""),
                         "phase_2": d["scope"]["name"] if d.get("scope", {}).get("items") else ""})
    return rows


def master_csv(cfg):
    rows = master(cfg)
    pw_cols = sorted({k for r in rows for k in r if k.startswith("pw_")}, key=lambda k: int(k.split("_")[1]))
    head = ["user_id", "client_id", "name", "email", "role", "company", "hub", "password", *pw_cols,
            "project_id", "project", "status", "live", "git", "railway", "account_email", "phase_2"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, head, restval="")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
