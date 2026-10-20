"""The owner's machine door into R-CAI: SCRN's WEB page reads the people and keeps the credit ledger (2026-10-19).

    GET  /r-cai/api/admin/people   Authorization: Bearer <stats key> -> {ok, users, signups, requests, credits}
    POST /r-cai/api/admin/credit   Authorization: Bearer <stats key>  {email, amount, note} -> {ok, balance}

The key is the same one SCRN already holds for VISITORS (Railway STATS_KEY_SHA256): one machine key, one owner.
No key / wrong key = 404, as if the door did not exist. Never returns a password hash, a code word or a cookie.

Credits: <store>/credits.jsonl, append-only (amount may be negative to use credit; a row is never edited or deleted).
<store> = RCAI_DATA_DIR (the Railway volume) or, locally, dta/_1_processed/rcai.
"""
import hashlib
import hmac
import importlib
import json
import os
import time
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
I = importlib.import_module("src_rcai.08_inbox")
U = importlib.import_module("src_rcai.05_users")


def authed(h):
    try:
        want = importlib.import_module("src_util_stats.stats")._key_hash()
    except Exception:
        return False
    got = (h.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
    return bool(want and got and hmac.compare_digest(hashlib.sha256(got.encode()).hexdigest(), want))


def _ledger():
    d = Path(os.environ["RCAI_DATA_DIR"]) if os.environ.get("RCAI_DATA_DIR") else C.ROOT / "dta" / "_1_processed" / "rcai"
    d.mkdir(parents=True, exist_ok=True)
    return d / "credits.jsonl"


def credits():
    f = _ledger()
    rows = []
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def balance(email, rows=None):
    email = (email or "").lower()
    return round(sum(r.get("amount", 0) for r in (rows if rows is not None else credits()) if r.get("email") == email), 2)


def add_credit(email, amount, note=""):
    email = (email or "").strip().lower()[:120]
    if "@" not in email:
        return None, "email?"
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        return None, "amount?"
    if not amount or abs(amount) > 100000:
        return None, "amount?"
    row = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(time.time()), "email": email,
           "amount": amount, "note": str(note or "")[:200]}
    with _ledger().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("RCAI_CREDIT " + json.dumps(row, ensure_ascii=False), flush=True)   # Railway's log keeps a copy
    return balance(email), ""


def people(cfg):
    led = credits()
    seen, users = set(), []
    for r in U.master(cfg):
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        users.append({k: r.get(k, "") for k in ("user_id", "name", "email", "company", "role", "hub", "password")}
                     | {"projects": sorted({x["project"] for x in U.master(cfg) if x["email"] == r["email"] and x["project"]}),
                        "credit": balance(r["email"], led)})
    rows = I.load()
    taps = {}                                                  # src_follow_up: doors tapped in the sign-up email
    try:
        for ln in (I.folder() / "doors.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(ln)
            taps.setdefault(d.get("email", ""), []).append(d.get("door", ""))
    except (OSError, ValueError):
        pass
    signups = [{k: r.get(k, "") for k in ("at", "email", "person", "company", "provider", "text")}
               | {"credit": balance(r.get("email"), led), "owner": r.get("owner", False),
                  "doors": taps.get((r.get("email") or "").lower(), [])}
               for r in rows if r.get("kind") == "signup"]
    requests = [{k: r.get(k, "") for k in ("at", "email", "person", "what", "project", "text")}
                for r in rows if r.get("kind") not in ("signup", "reader", "recruiter")]
    readers = [{k: r.get(k, "") for k in ("at", "ts", "email", "person", "company", "scale", "page", "src", "vid", "frame", "text")}
               for r in rows if r.get("kind") == "reader"]          # 2026-10-20: the article card (11_inbound reads it)
    raw_taps = []
    try:
        raw_taps = [json.loads(ln) for ln in (I.folder() / "doors.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    except (OSError, ValueError):
        pass
    return {"ok": True, "users": users, "signups": signups[::-1], "readers": readers[::-1], "taps": raw_taps[-500:],
            "requests": requests[::-1][:40], "credits": led[::-1][:40]}
