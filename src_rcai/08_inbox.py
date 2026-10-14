"""Every request a client SENDS from R-CAI lands here, then the sender waits 24 h: we write back in that window.

    put(cfg, email, kind, text, project, person, extra) -> (ok, until)   ok=False = still inside their 24 h (nothing saved)
    until(cfg, email)                                   -> epoch seconds the pause ends, 0 = free to send
    report(rows)                                        -> text, newest first (run.py --inbox)

Where it lands (one folder, he reads it):
  <store>/inbox/inbox.jsonl                          one row per request, append-only
  <store>/inbox/<YYYY-MM-DD>/<HHMMSS>_<who>_<kind>.md  the same request, readable
  stdout `RCAI_REQUEST {...}`                        Railway's log: hosted without a volume the folder forgets on
                                                     deploy, the log keeps it (run.py --inbox --log <saved log>)
  + one email to the admin per request (09_notify, Brevo): subject CLIENT req _from <name> _for <project> [client_id, project_id]
<store> = RCAI_DATA_DIR (a Railway volume) or, locally, dta/_0_raw/rcai_inbox (raw: what the client wrote, as written).

The pause counts only rows of the current state_epoch: run.py --fresh lifts every pause, the requests stay.
Stripe is never paused (it is a payment, not a request).
"""
import importlib
import json
import os
import re
import time
from pathlib import Path

C = importlib.import_module("src_rcai.01_config")

WAIT = 24 * 3600
KINDS = {
    "changes":  "Phase 1 edits",
    "build":    "Request build",
    "next":     "New project or phase",
    "demo":     "Request a demo",
    "action":   "Demo · request action",
    "plug":     "Plug-in",
    "prefs":    "Preferences + review",
    "feedback": "Feedback",
    "scope":    "Phase 2 · change the scope",
    "ship":     "Phase 2 · accepted · SHIP TODAY",
    "invoice":  "Phase 2 · invoice request",
    "support":  "Phase 2 · support plan · quick chat",
    "rebuild":  "Phase 2 · closed · request a different build",
    "signup":   "Sign up",
}


def folder():
    if os.environ.get("RCAI_DATA_DIR"):
        return Path(os.environ["RCAI_DATA_DIR"]) / "inbox"
    return C.RAW / "rcai_inbox"


def load(path=None):
    """Rows from inbox.jsonl, or from a saved Railway log (lines holding `RCAI_REQUEST {...}`)."""
    f = Path(path) if path else folder() / "inbox.jsonl"
    rows = []
    if not f.exists():
        return rows
    for line in f.read_text(encoding="utf-8").splitlines():
        if path and "RCAI_REQUEST" not in line:
            continue
        line = line[line.find("{"):] if "{" in line else ""
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("kind") in KINDS:
            rows.append(r)
    return rows


def until(cfg, email):
    email = (email or "").lower()
    ep = str(cfg.get("state_epoch", "1"))
    last = max((r.get("ts", 0) for r in load() if r.get("email") == email and str(r.get("epoch")) == ep), default=0)
    end = last + WAIT
    return end if end > time.time() else 0


def put(cfg, email, kind, text, project="", person="", extra=None):
    email = (email or "").lower()[:120]
    if kind not in KINDS:
        return False, 0
    wait = until(cfg, email)
    if wait:
        return False, wait
    now = time.time()
    row = {"at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)), "ts": int(now), "epoch": str(cfg.get("state_epoch", "1")),
           "email": email, "person": person or "", "owner": email in cfg["owners"], "kind": kind, "what": KINDS[kind],
           "project": project or "", "text": text}
    for k, v in (extra or {}).items():
        row[k] = v
    line = json.dumps(row, ensure_ascii=False)
    print("RCAI_REQUEST " + line, flush=True)
    try:
        d = folder()
        day = d / row["at"][:10]
        day.mkdir(parents=True, exist_ok=True)
        with (d / "inbox.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        who = re.sub(r"[^a-z0-9]+", "_", email.split("@")[0])[:24] or "anon"
        head = "\n".join(f"{k}: {row[k]}" for k in ("at", "what", "email", "person", "project") if row.get(k))
        more = "\n".join(f"{k}: {v}" for k, v in (extra or {}).items())
        (day / f"{row['at'][11:].replace(':', '')}_{who}_{kind}.md").write_text(
            f"# {KINDS[kind]}{' · ' + project if project else ''}\n\n{head}\n{more}\n\n---\n\n{text}\n", encoding="utf-8")
    except OSError:
        pass                                    # stdout already has it
    importlib.import_module("src_rcai.09_notify").admin(row, cfg)   # email to US (Brevo), in a thread; never to the client
    return True, int(now) + WAIT


def report(rows, everyone=True):
    rows = [r for r in rows if everyone or not r.get("owner")]
    if not rows:
        return "· no requests yet"
    out = []
    for r in sorted(rows, key=lambda r: r.get("ts", 0), reverse=True):
        due = time.strftime("%a %H:%M", time.localtime(r.get("ts", 0) + WAIT))
        out.append(f"\n{r['at'][5:16]}  {r['what']}{' · ' + r['project'] if r.get('project') else ''}"
                   f"   {r.get('person') or ''} {r['email']}{'  (owner test)' if r.get('owner') else ''}   reply by {due}")
        out.extend("    " + l for l in (r.get("text") or "-").splitlines()[:12])
    return "\n".join(out)
