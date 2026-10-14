"""The Clients Hub records, as a client may see them.

Reads the hub's people / companies / projects / access.json. Hands out ONLY the client-safe
fields below. Internal notes, money and estimates never leave this file -- the hub's records
disagree with each other on balances today, so billing stays off the portal until they agree.
One exception: a Phase 2 proposal's `price:` / add-on prices / `invoice:` lines in delivery.yml, written by hand.
"""
import base64
import json
import pathlib
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
# signed or paid: only then may a client ask for changes on that project (the key on its R-CAI square)
CAN_CHANGE = {"signed", "paid_in_build", "in_build", "phase1_delivered", "delivered", "live"}
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


# what a card may show about where the project lives, in this order
WHERE = ["live", "git", "railway", "email"]

# a status that asks something of the client becomes a notice. (lane, text)
STATUS_NOTICE = {
    "demo_sent": ("general", "A demo is waiting for your reaction."),
    "quoted": ("general", "A quote is waiting for your reply."),
    "pending_signature": ("general", "The proposal is waiting for your signature."),
    "phase1_delivered": ("deploy", "Phase 1 is delivered. Send changes any time."),
    "delivered": ("deploy", "Delivered. Send changes any time."),
}


def _delivery(path):
    """delivery.yml: `id:` blocks of `key: value` lines (stdlib only, the hosted repo has no yaml).
    notice lines repeat: `notice: deploy | text`. scope lines repeat: `scope: Phase 2 | one item`
    (the first part names the scope, the rest is one line of it; the client accepts or denies the whole)."""
    out, cur = {}, None
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        if not raw[0].isspace():
            cur = out.setdefault(k, {"notices": []})
        elif cur is not None and v:
            if k == "notice":
                lane, _, text = v.partition("|")
                cur["notices"].append({"lane": lane.strip() or "general", "text": text.strip() or lane.strip()})
            elif k == "scope":
                name, _, item = v.partition("|")
                sc = cur.setdefault("scope", {"name": name.strip(), "items": []})
                if item.strip():
                    sc["items"].append(item.strip())
            elif k == "addon":                    # `addon: Phase 2 | title | one line | 166` -- NOT in the build, offered FIRST.
                # 3-5 per phase (--check). Added = they join the deliverables and their price joins the total;
                # the page never says what one costs. Only these toggle, and only in "Ask to change the scope".
                name, _, rest = v.partition("|")
                title, _, rest = rest.partition("|")
                why, _, price = rest.partition("|")
                sc = cur.setdefault("scope", {"name": name.strip(), "items": []})
                if title.strip():
                    sc.setdefault("addons", []).append({"title": title.strip(), "why": why.strip(),
                                                        "p": int(re.sub(r"\D", "", price) or 0)})
            elif k == "price":                    # `price: 1660 | 50` -- the fixed total and the % paid to start
                tot, _, pct = v.partition("|")
                cur["price"] = {"base": int(re.sub(r"\D", "", tot) or 0), "pct": int(re.sub(r"\D", "", pct) or 50)}
            elif k == "timeline":                 # `timeline: when | what`, in order
                when, _, what = v.partition("|")
                cur.setdefault("timeline", []).append({"when": when.strip(), "what": what.strip()})
            elif k == "pay":                      # `pay: $3,250 | what it starts` -- the ONE money line, written on purpose
                amt, _, what = v.partition("|")
                cur["pay"] = {"amount": amt.strip(), "what": what.strip()}
            elif k == "invoice":                  # `invoice: <url>` = the build alone · `invoice: 3 | <url>` = with 3 add-ons in
                n, bar, url = v.partition("|")
                n, url = (n.strip(), url.strip()) if bar and n.strip().isdigit() else ("0", v)
                cur.setdefault("invoices", {})[n] = url
            elif k == "owner":                    # `owner: Cory Anderson | President` -- who owns the project, on its square
                name, _, role = v.partition("|")
                cur["owner"] = {"name": name.strip(), "role": role.strip()}
            elif k == "logo":                     # the client's own logo file, carried as a data URI: behind login, never in git
                f = (path.parent / v).resolve()
                mime = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(f.suffix.lower())
                if mime and f.exists():
                    cur["logo"] = f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
            elif k == "handbook":                 # the project's HANDBOOK (one PDF, the single source of truth): served behind login
                f = (path.parent / v).resolve()
                if f.suffix.lower() == ".pdf" and f.exists():
                    cur["handbook"] = str(f)
            elif k in WHERE:
                cur[k] = v
    return out


DOCS = pathlib.Path(__file__).parent / "20_docs"   # sealed handbooks: <id>.bin, the only form that ever reaches git


def _stream(data, key, nonce):
    import hashlib
    k = bytes.fromhex(key) + nonce
    stream = b"".join(hashlib.sha256(k + i.to_bytes(8, "big")).digest() for i in range(len(data) // 32 + 1))
    return bytes(a ^ b for a, b in zip(data, stream))


def seal(data, key):
    """SHA-256 counter keystream with a fresh 16-byte nonce up front (a re-sealed handbook never reuses a stream).
    The key never leaves the laptop + Railway."""
    import secrets
    nonce = secrets.token_bytes(16)
    return nonce + _stream(data, key, nonce)


def unseal(blob, key):
    return _stream(blob[16:], key, blob[:16])


def handbook_bytes(cfg, pid):
    """The HANDBOOK PDF of one project. Local: the file named in delivery.yml.
    Hosted: 20_docs/<id>.bin opened with the Railway variable RCAI_DOC_KEY (the repo is public; the bin alone reads as noise)."""
    import os
    if not cfg.get("hub_json"):
        f = (load(cfg).get("delivery", {}).get(pid) or {}).get("handbook")
        return pathlib.Path(f).read_bytes() if f and pathlib.Path(f).is_file() else None
    f, key = DOCS / f"{pid}.bin", os.environ.get("RCAI_DOC_KEY", "")
    if not key or not re.fullmatch(r"[\w-]+", pid) or not f.is_file():
        return None
    pdf = unseal(f.read_bytes(), key)
    return pdf if pdf.startswith(b"%PDF-") else None


def load(cfg):
    if cfg.get("hub_json"):                       # hosted: the snapshot from RCAI_HUB_JSON
        db = json.loads(cfg["hub_json"])
        db.setdefault("delivery", {})
        return db
    hub = cfg["hub"]
    return {
        "people": _read(hub / "people"),
        "companies": _read(hub / "companies"),
        "projects": _read(hub / "projects"),
        "access": {k: v for k, v in json.loads((hub / "access.json").read_text(encoding="utf-8")).items()
                   if not k.startswith("_")},
        "delivery": _delivery(hub / "delivery.yml"),
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
    d = db.get("delivery", {}).get(pid, {})
    if not d.get("live") and cfg["links"].get(pid):
        d = {**d, "live": cfg["links"][pid]}
    notices = list(d.get("notices", []))
    if p.get("status") in STATUS_NOTICE:
        lane, text = STATUS_NOTICE[p["status"]]
        notices.insert(0, {"lane": lane, "text": text})
    scope = d.get("scope")
    if scope and scope["items"]:
        notices.append({"lane": "scope", "text": f"{scope['name']} scope is waiting for your answer."})
    return {
        "where": [{"k": k, "v": d[k]} for k in WHERE if d.get(k)],
        "notices": notices,
        "scope": ({**scope, "timeline": d.get("timeline", []), "pay": d.get("pay"), "price": d.get("price"),
                   "pay_links": d.get("invoices", {})} if scope and scope["items"] else None),
        "logo": d.get("logo"),                  # the client's logo (data URI): on the square and the phase 2 page
        "owner": d.get("owner"),                # {name, role}: "Owned by" on the square
        "handbook": bool(d.get("handbook")),    # → api/handbook/<id>: the project's HANDBOOK PDF, behind login
        "id": pid,
        "code": p.get("project_id"),
        "name": p.get("name"),
        "company": company.get("name"),
        "kind": company.get("kind"),
        "demo": p.get("status") == "demo_sent",
        "can_change": p.get("status") in CAN_CHANGE,
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
        return {"name": "Yeriko", "role": "Owner", "company": "Custom AI Models", "owner": True, "email": email,
                "clients": len({c["company"] for c in cards}), "projects": cards}
    person = person_by_email(db, email)
    if not person or not person.get("hub"):
        return None
    ids = [pid for pid in db["access"].get(person["id"], []) if pid in db["projects"]]
    company = db["companies"].get(person.get("company"), {})
    cards = [_card(db, cfg, pid) for pid in ids]
    return {"name": person["name"].split()[0], "full": person["name"], "role": person.get("role"),
            "company": company.get("name"), "owner": False, "email": email,
            "logo": next((c["logo"] for c in cards if c.get("logo")), None),
            "projects": cards}


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
    delivery = {k: ({**v, "handbook": True} if v.get("handbook") else v)       # never a local path: the PDF rides in RCAI_DOC_* vars
                for k, v in db.get("delivery", {}).items() if k in projects}
    return {"people": people, "companies": companies, "projects": projects, "access": access, "delivery": delivery}
