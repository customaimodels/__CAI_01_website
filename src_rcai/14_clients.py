"""MAKE CLIENT: a sign-up becomes a hub holder in one press (2026-10-19, Phase 1 of the stranger-zone plan).

    run.py --make-client EMAIL --name "Maria Lopez" --company "Bloomfield Dental"     code word read from stdin, never argv

What one press does, in order, and nothing else:
    1  people/<id>.json        hub: true, a new client_id (Name_cNNN), a dated note
    2  companies/<id>.json     only if that company is new
    3  access.json             <id>: []   (an empty hub; projects are added by hand, as before)
    4  users.csv               the code word's hash as that email's next pw_N (never the word)
    5  welcome text            dta/_1_processed/rcai/_handoff/welcome_<id>.txt (0600), shown to him once
    6  Railway                 RCAI_USERS_JSON then RCAI_HUB_JSON, both through stdin (one redeploy, nothing printed)

Refuses: an owner, an email already on a hub, a bad email, a code word under 4 characters.
Before step 6 it proves the new snapshots differ from the old ones ONLY by this person: John, Cory and
Schuggie can never be changed by this key.
"""
import copy
import importlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
R = importlib.import_module("src_rcai.02_records")
U = importlib.import_module("src_rcai.05_users")
EMAIL = re.compile(r"[^@\s|,]+@[^@\s|,]+\.[a-z]{2,}")
HANDOFF = C.PROC / "rcai" / "_handoff"
RAILWAY = {"project": "b03b63c5-5ff3-49eb-9317-06f1cde087fe",       # CAI (same ids as run.py)
           "service": "1f34d884-c33b-4a9b-ae38-b77350d276ca",       # __CAI_01_website
           "environment": "df1aad77-2f5d-46ab-be4a-49cd7fc3ca68"}   # production


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:40]


def _next_client_no(hub):
    nums = [int(m.group(1)) for f in (hub / "people").glob("*.json")
            for m in [re.search(r"_c(\d+)$", json.loads(f.read_text(encoding="utf-8")).get("client_id") or "")] if m]
    return max(nums + [20]) + 1


def welcome(name, email, code, base="https://customaimodels.com"):
    first = (name or "there").split()[0]
    return (f"Subject: Your Custom AI Models hub is open\n\nHi {first},\n\n"
            "Thanks for the note. I read what you sent and opened a hub for you: it is where your project,\n"
            "files and next steps will live.\n\n"
            f"  Link:      {base}/r-cai/\n  Email:     {email}\n  Password:  {code}\n\n"
            "It starts empty. Reply to this email with anything that helps me see the problem\n"
            "(a sample file, a screenshot, how the work is done today) and the first piece goes in there.\n\n"
            "You can change the password from the gear once you are in.\n\n"
            "Yeriko Vargas\nCustom AI Models\n")


def make(email, name, company, code, cfg=None, push=True):
    """-> (ok, msg, welcome_text). cfg may point at a scratch hub (tests); push=False never touches Railway."""
    cfg = cfg or C.load()
    email, name, company = (email or "").strip().lower(), (name or "").strip()[:60], (company or "").strip()[:80]
    if not EMAIL.fullmatch(email):
        return False, "email?", ""
    if email in cfg["owners"]:
        return False, "that is an owner: owners keep their own door", ""
    if len(code or "") < 4:
        return False, "code word: 4+ characters", ""
    if cfg.get("hub_json") or U.store() is None:
        return False, "make clients on the laptop (the hosted copy is read-only)", ""
    hub = Path(cfg["hub"])
    db = R.load(cfg)
    if R.person_by_email(db, email):
        return False, f"{email} is already on a hub", ""
    before_hub, before_users = R.snapshot(cfg), U.snapshot()

    pid = _slug(name or email.split("@")[0])
    while (hub / "people" / f"{pid}.json").exists():
        pid += "-2"
    cid = _slug(company) or pid
    stamp = time.strftime("%Y-%m-%d")
    person = {"id": pid, "client_id": f"{(name or pid).split()[0].title()}_c{_next_client_no(hub):03d}",
              "name": name or email.split("@")[0], "company": cid, "role": "", "email": email,
              "is_buyer": True, "hub": True, "notes": [f"{stamp}: made a client from a sign-up (MAKE CLIENT, WEB)."],
              "source": "R-CAI sign-up"}
    (hub / "people" / f"{pid}.json").write_text(json.dumps(person, indent=2) + "\n", encoding="utf-8")
    if not (hub / "companies" / f"{cid}.json").exists():
        (hub / "companies" / f"{cid}.json").write_text(json.dumps(
            {"id": cid, "name": company or name or email, "kind": None, "notes": [f"{stamp}: from a sign-up."],
             "source": "R-CAI sign-up"}, indent=2) + "\n", encoding="utf-8")
    af = hub / "access.json"
    acc = json.loads(af.read_text(encoding="utf-8"))
    acc[pid] = []
    af.write_text(json.dumps(acc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    U.change(email, code)

    after_hub, after_users = R.snapshot(cfg), U.snapshot()
    bad = _only_added(before_hub, after_hub, before_users, after_users, pid, email)
    if bad:
        return False, "stopped before Railway: " + bad, ""
    text = welcome(person["name"], email, code)
    HANDOFF.mkdir(parents=True, exist_ok=True)
    out = HANDOFF / f"welcome_{pid}.txt"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    if not push:
        return True, f"{email} is a client locally ({pid}) · Railway not touched", text
    ok, msg = _railway(after_users, after_hub)
    return ok, (f"{email} is a client ({pid}) · live in ~1 min" if ok else f"{pid} made locally · Railway: {msg}"), text


def _only_added(bh, ah, bu, au, pid, email):
    """'' when the new snapshots equal the old ones plus this one person; else what else moved."""
    h = copy.deepcopy(ah)
    h["people"].pop(pid, None)
    h["access"].pop(pid, None)
    for c in set(h["companies"]) - set(bh["companies"]):
        h["companies"].pop(c)
    if h != bh:
        return "the hub snapshot changed for someone else"
    u = copy.deepcopy(au["users"])
    u[email] = u.get(email, [])[:len(bu["users"].get(email, []))]
    if not bu["users"].get(email):
        u.pop(email, None)
    if u != bu["users"]:
        return "the users snapshot changed for someone else"
    return ""


def _railway(users, hub):
    base = ["railway", "variable", "set", "-p", RAILWAY["project"], "-s", RAILWAY["service"], "-e", RAILWAY["environment"]]
    for key, val, quiet in (("RCAI_USERS_JSON", users, True), ("RCAI_HUB_JSON", hub, False)):
        raw = json.dumps(val, separators=(",", ":"))
        try:
            p = subprocess.run(base + ["--stdin", key] + (["--skip-deploys"] if quiet else []), input=raw,
                               capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, e.__class__.__name__
        if p.returncode:
            return False, f"{key} not set ({(p.stderr or p.stdout).strip().splitlines()[-1][:80] if (p.stderr or p.stdout).strip() else p.returncode})"
    return True, ""
