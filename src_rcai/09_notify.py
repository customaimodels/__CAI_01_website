"""Every request a client SENDS (08_inbox.put) emails US, never them: one Brevo transactional mail to the admin.

    admin(row)  -> starts a thread, returns at once. A failed send never blocks or undoes the request.

Subject  CLIENT req _from <person> _for <project> [<client_id>, <project_id>]
Body     one dark banner (the live gold knot PNG, gold rule) · one line of what happened · who · project · reply-by · their words.
Clients get nothing yet (testing). Nothing opens a mail app anywhere in R-CAI.

Config (config.yml, flat):  admin_email · admin_from · admin_from_name · public_url
Secret: BREVO_API_KEY -- Railway variable hosted; locally from the environment or src_util_emails/.env (gitignored).
Each try prints `RCAI_NOTIFY {...}` (Railway log) and, locally, appends to <inbox>/notify.log.
"""
import html
import json
import os
import threading
import time
import urllib.error
import urllib.request

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


def subject(row):
    who = row.get("person") or row.get("email")
    proj = row.get("project_name") or row.get("project") or "no project"
    return f"CLIENT req _from {who} _for {proj} [{row.get('client_id') or '-'}, {row.get('project_id') or '-'}]"


def _line(row):
    who = row.get("person") or row.get("email")
    co = f" ({row['company']})" if row.get("company") else ""
    on = f" on {row.get('project_name') or row['project']}" if row.get("project") else ""
    return f"{who}{co} sent “{row['what']}”{on} at {row['at'][11:16]} on {row['at'][:10]}."


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
    return f"""<!doctype html><html><body style="margin:0;background:{PAPER}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border:1px solid #e7e3da">
<tr><td style="background:{NIGHT};padding:16px 24px">
  <img src="{e(knot)}" width="26" height="26" alt="" style="vertical-align:middle;border:0">
  <span style="vertical-align:middle;margin-left:10px;color:#fff;font:600 15px -apple-system,Helvetica,Arial,sans-serif;letter-spacing:.02em">R-CAI</span>
  <span style="vertical-align:middle;margin-left:8px;color:{GOLD};font:11px ui-monospace,Menlo,monospace;letter-spacing:.14em">ADMIN · CLIENT REQUEST</span>
</td></tr>
<tr><td style="height:3px;background:{GOLD};font-size:0;line-height:0">&nbsp;</td></tr>
<tr><td style="padding:24px 24px 8px;color:{INK};font:600 18px/1.4 -apple-system,Helvetica,Arial,sans-serif">{e(_line(row))}</td></tr>
<tr><td style="padding:4px 24px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>
<tr><td style="padding:0 24px"><div style="color:{MUTE};font:11px ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;padding:8px 0;border-top:1px solid #eee">What they wrote</div></td></tr>
<tr><td style="padding:0 24px 24px;color:{INK};font:14px/1.6 -apple-system,Helvetica,Arial,sans-serif">{words}</td></tr>
<tr><td style="padding:14px 24px;border-top:1px solid #eee;color:{MUTE};font:11px ui-monospace,Menlo,monospace">They see “Sent · we write back within 24 hours”. Saved in the R-CAI inbox · run.py --inbox</td></tr>
</table></td></tr></table></body></html>"""


def text(row):
    return f"{_line(row)}\n\n" + "\n".join(f"{k}: {row.get(k)}" for k in ("email", "company", "client_id", "project_id") if row.get(k)) \
        + f"\n\n{row.get('text') or '-'}\n"


def _send(row, cfg):
    out = {"at": row["at"], "kind": row["kind"], "email": row.get("email"), "to": cfg.get("admin_email")}
    key = _key()
    if not key or not cfg.get("admin_email"):
        out["ok"], out["why"] = False, "no BREVO_API_KEY" if not key else "no admin_email"
    else:
        msg = {"sender": {"name": cfg.get("admin_from_name", "R-CAI"), "email": cfg.get("admin_from") or cfg["admin_email"]},
               "to": [{"email": cfg["admin_email"]}], "subject": subject(row), "htmlContent": body(row, cfg),
               "textContent": text(row), "tags": ["rcai-admin", row["kind"]]}
        if row.get("email") and "@" in row["email"]:
            msg["replyTo"] = {"email": row["email"], "name": row.get("person") or row["email"]}
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
