"""The Clients Hub records, as a client may see them.

Reads the hub's people / companies / projects / access.json. Hands out ONLY the client-safe
fields below. Internal notes, money and estimates never leave this file -- the hub's records
disagree with each other on balances today, so billing stays off the portal until they agree.
"""
import json
import re

# money never reaches a client: any phase part / note sentence naming it is dropped
MONEY = re.compile(r"invoice|retainer|paid|payment|balance|deposit|outstanding|\bowe|\$|€|£", re.I)

# the growth line: every status sits on it. seed → planted → growing → delivered → runs
STAGES = ["Seed", "Planted", "Growing", "Delivered", "Runs"]
STATUS = {
    "demo_sent":        (0, "Demo sent"),
    "quoted":           (0, "Quoted"),
    "pending_signature": (0, "Pending signature"),
    "signed":           (1, "Signed · in build"),
    "paid_in_build":    (2, "In build"),
    "in_build":         (2, "In build"),
    "phase1_delivered": (3, "Phase 1 delivered"),
    "delivered":        (3, "Delivered"),
    "live":             (4, "Live"),
}
DATE_LABELS = [("added", "Opened"), ("demo_sent", "Demo sent"), ("signed", "Signed"),
               ("delivery", "Delivery")]


def _clean_phase(text):
    parts = [x.strip() for x in (text or "").split("·") if x.strip() and not MONEY.search(x)]
    return " · ".join(parts) or None


def _clean_note(text):
    keep = [x for x in re.split(r"(?<=[.!?])\s+", text or "") if x and not MONEY.search(x)]
    return " ".join(keep) or None


def _read(folder):
    out = {}
    for f in sorted(folder.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["id"]] = d
    return out


def load(cfg):
    if cfg.get("hub_json"):                       # hosted: the snapshot from RCAI_HUB_JSON
        return json.loads(cfg["hub_json"])
    hub = cfg["hub"]
    return {
        "people": _read(hub / "people"),
        "companies": _read(hub / "companies"),
        "projects": _read(hub / "projects"),
        "access": {k: v for k, v in json.loads((hub / "access.json").read_text(encoding="utf-8")).items()
                   if not k.startswith("_")},
    }


def person_by_email(db, email):
    email = email.strip().lower()
    for p in db["people"].values():
        if (p.get("email") or "").lower() == email:
            return p
    return None


def _card(db, cfg, pid):
    p = db["projects"][pid]
    stage, label = STATUS.get(p.get("status"), (0, (p.get("status") or "").replace("_", " ").title()))
    dates = [{"k": lab, "v": p["dates"][k]} for k, lab in DATE_LABELS if (p.get("dates") or {}).get(k)]
    company = db["companies"].get(p.get("company"), {})
    return {
        "id": pid,
        "code": p.get("project_id"),
        "name": p.get("name"),
        "company": company.get("name"),
        "kind": company.get("kind"),
        "demo": p.get("status") == "demo_sent",
        "stage": stage,
        "stage_label": label,
        "phase": _clean_phase(p.get("phase")),
        "note": _clean_note(p.get("client_note")),
        "dates": dates,
        "link": cfg["links"].get(pid),
    }


def view(db, cfg, email):
    """What one signed-in email may see. None = not a hub holder."""
    email = email.strip().lower()
    if email in cfg["owners"]:
        cards = [_card(db, cfg, pid) for pid in db["projects"]]
        return {"name": "Yeriko", "role": "Owner", "company": "Custom AI Models", "owner": True,
                "clients": len({c["company"] for c in cards}), "projects": cards}
    person = person_by_email(db, email)
    if not person or not person.get("hub"):
        return None
    ids = [pid for pid in db["access"].get(person["id"], []) if pid in db["projects"]]
    company = db["companies"].get(person.get("company"), {})
    return {"name": person["name"].split()[0], "full": person["name"], "role": person.get("role"),
            "company": company.get("name"), "owner": False,
            "projects": [_card(db, cfg, pid) for pid in ids]}


def stages():
    return STAGES


def snapshot(cfg):
    """The hosted copy of the hub: only the fields view() reads, money already cleaned out.
    Goes into the Railway variable RCAI_HUB_JSON, never into git."""
    db = load(cfg)
    keep = lambda d, ks: {k: d[k] for k in ks if d.get(k) is not None}
    people = {i: keep(p, ("id", "name", "email", "role", "company", "hub")) for i, p in db["people"].items() if p.get("hub")}
    projects = {}
    for i, p in db["projects"].items():
        q = keep(p, ("id", "project_id", "name", "company", "status"))
        q["dates"] = {k: v for k, v in (p.get("dates") or {}).items() if v and k in dict(DATE_LABELS)}
        q["phase"] = _clean_phase(p.get("phase"))
        q["client_note"] = _clean_note(p.get("client_note"))
        projects[i] = q
    companies = {i: keep(c, ("id", "name", "kind")) for i, c in db["companies"].items()}
    access = {k: v for k, v in db["access"].items() if k in people}
    return {"people": people, "companies": companies, "projects": projects, "access": access}
