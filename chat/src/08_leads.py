"""The 3-line Name / Email / Project reply becomes one row in dta/_2_exports/leads.csv (+ optional webhook)."""
import csv
import json
import re
from datetime import datetime, timezone
from importlib import import_module
from urllib import request

P = import_module("src.01_paths")
C = import_module("src.02_config")

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEAD = ["timestamp_utc", "session_id", "name", "email", "project"]


def parse(text):
    got = {}
    for line in text.splitlines():
        k, _, v = line.partition(":")
        k = k.strip().lower()
        if k in ("name", "email", "project") and v.strip():
            got[k] = v.strip()
    if len(got) == 3 and EMAIL.match(got["email"]):
        return got
    return None


def save(session_id, lead):
    row = {"timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "session_id": session_id, **lead}
    P.LEADS.parent.mkdir(parents=True, exist_ok=True)
    new = not P.LEADS.exists()
    with P.LEADS.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, HEAD)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"[CAI LEAD] {row['timestamp_utc']} session={session_id}", flush=True)  # pointer, not content
    url = C.get("lead_webhook_url", "")
    if url:
        try:
            req = request.Request(url, json.dumps(row).encode(), {"Content-Type": "application/json"})
            request.urlopen(req, timeout=5).close()
        except Exception as e:
            print(f"[CAI LEAD] webhook failed: {e}", flush=True)
    return row
