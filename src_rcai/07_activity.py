"""What a client DID on a Phase 2 page, and where they stand: the road has to end in one of the exits.

    record(cfg, email, p, act, extra) -> one row appended to activity.jsonl + one `RCAI_EVENT {...}` line on stdout
                                         (stdout = Railway's logs, the only thing that outlives a deploy without a volume)
    report(rows, who, everyone)       -> text: per person × project, the steps in order + the verdict

The road (rank = how far along):
  1 open      opened the Phase 2 page
  2 package   added the package · took an add-on out/in · opened "Ask to change the scope"
  3 scope     saved scope notes · sent them to the second reader
  4 decide    sent a scope change · pressed Accept now, pay later
  5 EXIT      SHIP TODAY · opened Stripe · requested an invoice

Only acts in ACTS are kept. Rows hold pointers (who, which project, which step, picks, total), never note text.
"""
import importlib
import json
import os
import time
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")
U = importlib.import_module("src_rcai.05_users")

ACTS = {
    "open":        (1, "opened Phase 2"),
    "add_pkg":     (2, "added the package"),
    "addon_off":   (2, "took an add-on out"),
    "addon_on":    (2, "put an add-on back"),
    "scope_open":  (2, "opened Ask to change the scope"),
    "scope_saved": (3, "saved scope notes"),
    "scope_check": (3, "sent notes to the second reader"),
    "scope_sent":  (4, "SENT a scope change"),
    "accept":      (4, "pressed Accept now, pay later"),
    "not_yet":     (4, "backed off: Not yet"),
    "ship":        (5, "SHIP TODAY"),
    "stripe":      (5, "opened Stripe"),
    "invoice":     (5, "requested an invoice"),
}
EXITS = {"ship": "ACCEPTED · ship today", "stripe": "PAYING · opened Stripe", "invoice": "PAYING · asked for an invoice",
         "scope_sent": "SCOPE CHANGE · in review (24 h)"}


def where():
    """Same folder as users.csv when there is one (local, or a Railway volume); hosted without one, the container's
    own dta (forgets on deploy -- stdout keeps the copy)."""
    return (U.store() or C.PROC / "rcai") / "activity.jsonl"


def record(cfg, email, p, act, extra=None, person=""):
    if act not in ACTS:
        return False
    row = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "email": email, "person": person or "", "owner": email in cfg["owners"],
           "project": p.get("code") or p.get("name"), "name": p.get("name"), "act": act}
    for k, v in (extra or {}).items():
        if k in ("picked", "total", "deposit") and isinstance(v, (int, float, list)):
            row[k] = v if not isinstance(v, list) else [int(x) for x in v if isinstance(x, (int, float))][:8]
    line = json.dumps(row, ensure_ascii=False)
    print("RCAI_EVENT " + line, flush=True)
    try:
        f = where()
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass                                    # stdout already has it
    return True


def load(path=None):
    """Rows from activity.jsonl, or from a saved Railway log (lines holding `RCAI_EVENT {...}`)."""
    f = Path(path) if path else where()
    rows = []
    if not f.exists():
        return rows
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line[line.find("{"):] if "{" in line else ""
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("act") in ACTS:
            rows.append(r)
    return rows


def verdict(steps):
    """The furthest exit wins; no exit = STUCK at the furthest step."""
    acts = [s["act"] for s in steps]
    for a in ("ship", "stripe", "invoice", "scope_sent"):
        if a in acts:
            return "✓ " + EXITS[a]
    top = max(steps, key=lambda s: (ACTS[s["act"]][0], s["at"]))
    return f"! STUCK · furthest: {ACTS[top['act']][1]}"


def report(rows, who=None, everyone=False):
    hit = lambda r: who.lower() in " ".join(str(r.get(k, "")) for k in ("email", "person", "project", "name")).lower()
    rows = [r for r in rows if (everyone or not r.get("owner")) and (not who or hit(r))]
    if not rows:
        return "· no Phase 2 activity yet" + ("" if everyone else " (owners hidden: --all shows them)")
    groups = {}
    for r in rows:
        groups.setdefault((r["email"], r["project"]), []).append(r)
    out = []
    for (email, proj), steps in sorted(groups.items(), key=lambda kv: kv[1][-1]["at"], reverse=True):
        steps.sort(key=lambda s: s["at"])
        out.append(f"\n{steps[0].get('name') or proj} · {steps[-1].get('person') or ''} {email}".replace("  ", " "))
        out.append(f"  {verdict(steps)}   · {len(steps)} steps · first {steps[0]['at']} · last {steps[-1]['at']}")
        last = None
        for s in steps:
            if s["act"] == last == "open":
                continue                        # page reloads say nothing
            money = f"   total ${s['total']:,}" if isinstance(s.get("total"), (int, float)) else ""
            out.append(f"  {s['at'][5:16]}  {ACTS[s['act']][0]}  {ACTS[s['act']][1]}{money}")
            last = s["act"]
    return "\n".join(out)
