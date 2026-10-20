"""Every request a client SENDS (08_inbox.put) emails US, never them: one Brevo transactional mail to the admin.

    admin(row)  -> starts a thread, returns at once. A failed send never blocks or undoes the request.

Subject  CLIENT req _from <person> _for <project> [<client_id>, <project_id>]
Body     one dark banner (the live gold knot PNG, gold rule) · one line of what happened · who · project · reply-by · their words.
Clients get nothing yet (testing), with ONE exception (2026-10-18, his word): a Google/Microsoft sign-up gets
"we have your request" at its VERIFIED email -- received(row, cfg). Its layout is MARKETING's (12_mail/, frozen from __ss3_mketing/_src_util_emails). Fake domains (.test .example .invalid .local) and
RCAI_MAIL_DRY=1 are logged, never sent. Nothing opens a mail app anywhere in R-CAI.

Config (config.yml, flat):  admin_email · admin_from · admin_from_name · public_url
Secret: BREVO_API_KEY -- Railway variable hosted; locally from the environment or src_util_emails/.env (gitignored).
Each try prints `RCAI_NOTIFY {...}` (Railway log) and, locally, appends to <inbox>/notify.log.
"""
import html
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

C = __import__("importlib").import_module("src_rcai.01_config")

API = "https://api.brevo.com/v3/smtp/email"
GOLD, NIGHT, PAPER, INK, MUTE = "#d9a62c", "#0e0c12", "#faf8f3", "#1a1820", "#77737f"


def _key():
    if os.environ.get("BREVO_API_KEY"):
        return os.environ["BREVO_API_KEY"]
    env = C.ROOT / "src_util_emails" / ".env"                      # local only, never bundled
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("BREVO_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


# kind -> (TAG first in the subject, what they did, YOUR MOVE). Money first: the tag says it before the name does.
# Lean: one verb, one fact, one move (jobsy-mail voice: plain, certain, no "just wanted to").
SAY = {
    "ship":     ("$ ACCEPTED", "accepted Phase 2 and said ship today", "Confirm the start date and send the build plan. The deposit link is already live."),
    "invoice":  ("$ INVOICE", "asked for an invoice", "Send the invoice in the payment method they picked (below)."),
    "scope":    ("SCOPE CHANGE", "asked to change the Phase 2 scope", "Answer each note with a revised scope. Their Accept stays frozen until you do."),
    "rebuild":  ("! CLOSED", "closed the Phase 2 proposal and wants a different build", "Write back today: ask what build they want instead."),
    "changes":  ("EDITS", "sent Phase 1 edits", "Fix it or say when it will be fixed."),
    "build":    ("NEW BUILD", "requested a new build", "Offer a 20-minute scope call."),
    "next":     ("NEW PHASE", "wants a new project or phase", "Offer a 20-minute scope call."),
    "demo":     ("DEMO", "requested a demo", "Reply with a demo time."),
    "action":   ("DEMO ACTION", "acted on a demo", "Do what they ticked (below)."),
    "plug":     ("PLUG-IN", "asked about a plug-in", "Reply with what it does for them and what it costs."),
    "prefs":    ("REVIEW", "rated us and set preferences", "Thank them. A 4 or 5: ask for the public review."),
    "feedback": ("FEEDBACK", "sent feedback", "Read it. Reply if it needs an answer."),
    "support":  ("SUPPORT", "opened a quick chat about the support plan", "Reply today."),
    "signup":   ("SIGN UP", "asked for R-CAI access", "Check who they are, then add them to access.json and send the code word."),
    "recruiter": ("RECRUITER", "asked for the recruiter access code", "Check the company and the role. A fit: send the code (or a personal link, run.py --recruiter-link)."),
    "reader":   ("READER", "answered the question card on an article", "Reply within 24 h from yeriko@, one line on their problem, one question back."),
}


def _say(row):
    return SAY.get(row.get("kind"), (row.get("what", "REQUEST").upper(), f"sent “{row.get('what')}”", "Write back within 24 hours."))


def subject(row):
    """CLIENT req · <TAG> _from <name> _for <project> [client_id, project_id] -- his skeleton, the tag says what it is."""
    who = row.get("person") or row.get("email")
    proj = row.get("project_name") or row.get("project") or "no project"
    return f"CLIENT req · {_say(row)[0]} _from {who} _for {proj} [{row.get('client_id') or '-'}, {row.get('project_id') or '-'}]"


def _gist(row, n=90):
    t = " ".join((row.get("text") or "").split())
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def _line(row):
    who = row.get("person") or row.get("email")
    co = f" ({row['company']})" if row.get("company") else ""
    on = f" · {row.get('project_name') or row['project']}" if row.get("project") else ""
    return f"{who}{co} {_say(row)[1]}{on}."


def body(row, cfg):
    e = html.escape
    due = time.strftime("%a %d %b · %H:%M", time.localtime(row["ts"] + 24 * 3600))
    facts = [("Client", f"{row.get('person') or '-'} · {row.get('email')}"), ("Company", row.get("company")),
             ("Client id", row.get("client_id")), ("Project", row.get("project_name") or row.get("project")),
             ("Project id", row.get("project_id")), ("Request", row["what"]), ("Reply by", due)]
    facts += [(k.title(), f"${row[k]:,}" if isinstance(row[k], (int, float)) else row[k]) for k in ("deposit", "total") if row.get(k)]
    if row.get("owner"):
        facts.append(("Note", "owner test, sent from your own login"))
    rows = "".join(f'<tr><td style="padding:6px 0;color:{MUTE};font:11px ui-monospace,Menlo,monospace;letter-spacing:.06em;'
                   f'text-transform:uppercase;width:120px;vertical-align:top">{e(k)}</td>'
                   f'<td style="padding:6px 0;color:{INK};font:14px -apple-system,Helvetica,Arial,sans-serif">{e(str(v))}</td></tr>'
                   for k, v in facts if v)
    words = e(row.get("text") or "-").replace("\n", "<br>")
    knot = cfg.get("public_url", "").rstrip("/") + "/03_img/05_knot_gold.png"
    tag, _, move = _say(row)
    pre = e(f"{_gist(row) or tag} · reply by {due}")              # the inbox preview line, hidden in the body
    return f"""<!doctype html><html><body style="margin:0;background:{PAPER}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border:1px solid #e7e3da">
<tr><td style="background:{NIGHT};padding:16px 24px">
  <img src="{e(knot)}" width="26" height="26" alt="" style="vertical-align:middle;border:0">
  <span style="vertical-align:middle;margin-left:10px;color:#fff;font:600 15px -apple-system,Helvetica,Arial,sans-serif;letter-spacing:.02em">R-CAI</span>
  <span style="vertical-align:middle;margin-left:8px;color:{GOLD};font:11px ui-monospace,Menlo,monospace;letter-spacing:.14em">{e(tag)}</span>
</td></tr>
<tr><td style="height:3px;background:{GOLD};font-size:0;line-height:0">&nbsp;</td></tr>
<tr><td style="padding:24px 24px 6px;color:{INK};font:600 19px/1.35 -apple-system,Helvetica,Arial,sans-serif">{e(_line(row))}</td></tr>
<tr><td style="padding:6px 24px 18px"><div style="border-left:3px solid {GOLD};padding:8px 12px;background:#fbf6e8">
  <span style="color:{MUTE};font:11px ui-monospace,Menlo,monospace;letter-spacing:.08em">YOUR MOVE · BY {e(due.upper())}</span><br>
  <span style="color:{INK};font:15px/1.5 -apple-system,Helvetica,Arial,sans-serif">{e(move)}</span></div></td></tr>
<tr><td style="padding:0 24px"><div style="color:{MUTE};font:11px ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;padding:8px 0;border-top:1px solid #eee">Their words</div></td></tr>
<tr><td style="padding:0 24px 18px;color:{INK};font:15px/1.6 -apple-system,Helvetica,Arial,sans-serif">{words}</td></tr>
<tr><td style="padding:4px 24px 12px;border-top:1px solid #eee"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>
<tr><td style="padding:14px 24px;border-top:1px solid #eee;color:{MUTE};font:11px ui-monospace,Menlo,monospace">Testing: replies stay with you, nothing reaches the client. They see “Sent · we write back within 24 hours”. Saved · run.py --inbox</td></tr>
</table></td></tr></table></body></html>"""


def text(row):
    return f"{_line(row)}\n\nYOUR MOVE: {_say(row)[2]}\n\n" + "\n".join(f"{k}: {row.get(k)}" for k in ("email", "company", "client_id", "project_id") if row.get(k)) \
        + f"\n\n{row.get('text') or '-'}\n"


def from_name(row):
    """What HE sees on the From line: RCAI | JohnW M&A · RCAI | CoryA M&A · RCAI | Schuggie Ceilidhs (no person = the company)."""
    co = (row.get("company") or "").replace("'s", "").replace("’s", "")
    name = (row.get("person") or "").split()
    if not name:
        return f"RCAI | {co or row.get('email') or 'client'}".strip()
    who = name[0] + (name[-1][0] if len(name) > 1 else "")
    return f"RCAI | {who} {co.split()[0] if co else ''}".strip()


def _send(row, cfg):
    out = {"at": row["at"], "kind": row["kind"], "email": row.get("email"), "to": cfg.get("admin_email")}
    key = _key()
    if not key or not cfg.get("admin_email"):
        out["ok"], out["why"] = False, "no BREVO_API_KEY" if not key else "no admin_email"
    else:
        msg = {"sender": {"name": from_name(row),"email": cfg.get("admin_from") or cfg["admin_email"]},
               "to": [{"email": cfg["admin_email"]}], "subject": subject(row), "htmlContent": body(row, cfg),
               "textContent": text(row), "tags": ["rcai-admin", row["kind"]]}
        # no replyTo while testing: a reply from his inbox must never reach a real client (YERIKO_SAYS 2026-10-14)
        req = urllib.request.Request(API, data=json.dumps(msg).encode(), method="POST",
                                     headers={"api-key": key, "content-type": "application/json", "accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                out["ok"], out["id"] = True, json.loads(r.read() or b"{}").get("messageId")
        except urllib.error.HTTPError as err:
            out["ok"], out["why"] = False, f"brevo {err.code}: {err.read().decode(errors='replace')[:200]}"
        except OSError as err:
            out["ok"], out["why"] = False, str(err)[:200]
    line = json.dumps(out, ensure_ascii=False)
    print("RCAI_NOTIFY " + line, flush=True)
    try:
        with (__import__("importlib").import_module("src_rcai.08_inbox").folder() / "notify.log").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    return out


def admin(row, cfg, wait=False):
    if wait:
        return _send(row, cfg)
    threading.Thread(target=_send, args=(row, cfg), daemon=True).start()
    return None


# ---- the one mail a person outside gets: their sign-up landed (2026-10-18) -------------------------------------------
FAKE = (".test", ".example", ".invalid", ".local", ".localhost")


MAIL = Path(__file__).resolve().parent / "12_mail"      # marketing's shell, frozen by 12_mail/sync_from_mketing.py


def received_body(row, cfg):
    """The marketing template (scoping_ack, light) with the slots filled. Layout is marketing's; only words live here."""
    e = html.escape
    first = (row.get("person") or "there").split()[0]
    shell = (MAIL / "scoping_ack.html").read_text(encoding="utf-8")
    need = (row.get("need") or "").strip()
    if not need:                                               # no "what you sent" row: drop the item block whole
        shell = re.sub(r'\n\s*<tr><td class="px" style="padding:0 40px 20px 40px;">.*?\{\{ITEM_TEXT\}\}.*?</td></tr>', "", shell, count=1, flags=re.S)
    doors = _doors_html(row, cfg)                              # src_follow_up: the door into their problem
    if doors:
        shell = re.sub(r'(\{\{BODY\}\}</p>)', lambda m: m.group(1) + doors, shell, count=1)
    fill = {"SUBJECT": "We have your request · Custom AI Models",
            "PREHEADER": "Which of these is closest? One tap tells us where to start.",
            "HEADLINE": f"Hi {e(first)}, we have your request.",
            "BODY": "A person reads it and writes back within 24 hours. To start sharper: these are the ways this usually breaks. Tap the one closest to yours.",
            "ITEM_TITLE": "What you sent", "ITEM_TEXT": e(need).replace("\n", "<br>"),
            "SENDER": "Yeriko · Custom AI Models",
            "FOOTER": "Custom AI Models · Est. 2022 · customaimodels.com. You get this because you signed up at R-CAI with this address. Nothing else follows unless you reply.",
            "PUBLIC_URL": e(cfg.get("public_url", "https://customaimodels.com").rstrip("/"))}
    for k, v in fill.items():
        shell = shell.replace("{{" + k + "}}", v)
    return shell


def _doors_html(row, cfg):
    """The 8 doors (src_follow_up/doors.json), closest to what they wrote first. Email-safe tables, inline styles.
    Each door is a signed /r-cai/api/door link: the click is logged for us, then lands on the page that answers it."""
    try:
        F = __import__("importlib").import_module("src_follow_up.follow")
        ranked = F.rank(row.get("need") or "")
    except Exception as err:                                   # no doors = the plain mail, never a failed send
        print("RCAI_NOTIFY " + json.dumps({"kind": "doors_off", "why": str(err)[:120]}), flush=True)
        return ""
    e, base = html.escape, cfg.get("public_url", "https://customaimodels.com").rstrip("/")
    cells = []
    for i, d in enumerate(ranked):
        top = i < 3 and d.get("score", 0) > 0.5
        rim = f"border-left:3px solid {GOLD};" if top else "border-left:3px solid #e6e1d6;"
        tag = (f'<span style="font-family:\'Courier New\',monospace;font-size:10px;letter-spacing:1px;color:{GOLD};">CLOSEST TO YOURS</span><br>'
               if top else "")
        cells.append(
            f'<tr><td style="padding:0 0 8px 0;"><a href="{e(F.link(row.get("email", ""), d["id"], base))}" '
            f'style="display:block;text-decoration:none;{rim}background:#ffffff;border-top:1px solid #e6e1d6;'
            f'border-right:1px solid #e6e1d6;border-bottom:1px solid #e6e1d6;padding:12px 14px;">'
            f'{tag}<span style="font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:{INK};">{e(d["title"])} &rarr;</span><br>'
            f'<span style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:{MUTE};">{e(d["line"])}</span></a></td></tr>')
    return ('\n          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            'style="margin:4px 0 18px 0;">' + "".join(cells) + "</table>")


def received_text(row):
    first = (row.get("person") or "there").split()[0]
    lines = ""
    try:
        F = __import__("importlib").import_module("src_follow_up.follow")
        lines = "\n".join(f"- {d['title']}: https://customaimodels.com{d['href']}?{F.doors()['utm']}&utm_content={d['id']}" for d in F.rank(row.get("need") or ""))
    except Exception:
        pass
    return (f"Hi {first}, we have your request.\n\nA person reads it and writes back within 24 hours. "
            f"The ways this usually breaks, closest to yours first:\n{lines}\n\nWhat you sent:\n{row.get('need') or '-'}\n\nCustom AI Models · customaimodels.com\n")


def _send_received(row, cfg):
    to = (row.get("email") or "").strip().lower()
    out = {"at": row.get("at"), "kind": "signup_received", "to": to}
    key = _key()
    if not to or "@" not in to:
        out["ok"], out["why"] = False, "no email"
    elif to.endswith(FAKE) or os.environ.get("RCAI_MAIL_DRY") == "1":
        out["ok"], out["why"] = True, "dry (fake domain or RCAI_MAIL_DRY), not sent"
    elif not key:
        out["ok"], out["why"] = False, "no BREVO_API_KEY"
    else:
        msg = {"sender": {"name": "YERIKO | CUSTOM AI", "email": cfg.get("admin_from") or cfg["admin_email"]},
               "to": [{"email": to, "name": row.get("person") or to}], "replyTo": {"email": cfg["admin_email"]},
               "subject": "We have your request · Custom AI Models", "htmlContent": received_body(row, cfg),
               "textContent": received_text(row), "tags": ["rcai-signup-received"]}
        req = urllib.request.Request(API, data=json.dumps(msg).encode(), method="POST",
                                     headers={"api-key": key, "content-type": "application/json", "accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                out["ok"], out["id"] = True, json.loads(r.read() or b"{}").get("messageId")
        except urllib.error.HTTPError as err:
            out["ok"], out["why"] = False, f"brevo {err.code}: {err.read().decode(errors='replace')[:200]}"
        except OSError as err:
            out["ok"], out["why"] = False, str(err)[:200]
    line = json.dumps(out, ensure_ascii=False)
    print("RCAI_NOTIFY " + line, flush=True)
    try:
        with (__import__("importlib").import_module("src_rcai.08_inbox").folder() / "notify.log").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    return out


def received(row, cfg, wait=False):
    if wait:
        return _send_received(row, cfg)
    threading.Thread(target=_send_received, args=(row, cfg), daemon=True).start()
    return None
