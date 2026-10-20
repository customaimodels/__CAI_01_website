"""The portal, mounted at /r-cai on whatever server carries the site (run.py locally, main.py on Railway).

    handle(h, "GET"|"POST") -> True if the request was /r-cai/..., answered here; False = not ours.

GET  /r-cai/            the page (src_rcai/10_web)
POST /r-cai/api/login   {email, code}  → sets the rcai cookie (Path=/r-cai)
GET  /r-cai/api/me      the signed-in view (records re-read every call: the hub is the truth)
POST /r-cai/api/password {current, new} → adds the next pw_N column (05_users), re-issues the cookie
GET  /r-cai/api/master.csv  owners only: the MASTER table, person × project
POST /r-cai/api/scope    {stage: check|review, i, notes, tries} → the Phase 2 scope reviewers (06_review, mock today)
POST /r-cai/api/event    {i, act, picked?, total?} → one step on a Phase 2 page (07_activity: where the client stands)
GET  /r-cai/api/handbook/<id>  the project's HANDBOOK PDF, only for someone who can see that project
GET  /r-cai/api/visual/<id>    the phase 2 picture (delivery.yml visual:), same rule
GET  /r-cai/api/logo/<id>      hosted: the client logo, sealed in 20_docs (local pages carry it as a data URI)
POST /r-cai/api/request  {kind, text, project?} → 08_inbox: saved, then that person waits 24 h (429 + until inside it)
GET  /r-cai/api/oauth/me · /api/oauth/<google|microsoft>/start · …/callback → 11_oauth (proves who, never opens a hub)
POST /r-cai/api/signup   {company, need} → 08_inbox kind=signup, ONLY behind a Google/Microsoft identity (rcai_id);
                         the email comes from that identity, never from the body (24 h per email, 3 a day per address)
GET  /r-cai/api/activity owners only: the Phase 2 activity report, as text
GET  /r-cai/api/admin/people · POST /r-cai/api/admin/credit  SCRN's machine key only (13_admin): people + credit ledger
POST /r-cai/api/logout
"""
import importlib
import json
import mimetypes
import os
import time
import urllib.parse
from http.cookies import SimpleCookie

C = importlib.import_module("src_rcai.01_config")
R = importlib.import_module("src_rcai.02_records")
A = importlib.import_module("src_rcai.03_auth")
U = importlib.import_module("src_rcai.05_users")
V = importlib.import_module("src_rcai.06_review")
T = importlib.import_module("src_rcai.07_activity")
I = importlib.import_module("src_rcai.08_inbox")
N = importlib.import_module("src_rcai.09_notify")
O = importlib.import_module("src_rcai.11_oauth")
ADM = importlib.import_module("src_rcai.13_admin")
CFG = None


def _cfg():
    global CFG
    CFG = CFG or C.load()
    return CFG


def _send(h, code, body, ctype, cookie=None, cache="no-store"):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Cache-Control", cache)
    h.send_header("X-Frame-Options", "DENY")
    h.send_header("Referrer-Policy", "no-referrer")
    if cookie is not None:
        h.send_header("Set-Cookie", cookie)
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)
    return True


def _json(h, code, obj, cookie=None):
    return _send(h, code, json.dumps(obj).encode(), "application/json", cookie)


def _ip(h):
    """Behind Railway's proxy every visitor shares one socket address: use the forwarded one there."""
    fwd = h.headers.get("X-Forwarded-For", "") if os.environ.get("PORT") else ""
    return fwd.split(",")[0].strip() or h.client_address[0]


def _email(h):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    return A.read(jar["rcai"].value) if "rcai" in jar else None


def _cookie(value, age):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"rcai={value}; Path={C.MOUNT}; Max-Age={age}; HttpOnly; SameSite=Strict{secure}"


def _jar(h, name):
    jar = SimpleCookie(h.headers.get("Cookie", ""))
    return jar[name].value if name in jar else ""


def _oa_cookie(name, value, age, path):
    secure = "; Secure" if os.environ.get("PORT") else ""
    return f"{name}={value}; Path={path}; Max-Age={age}; HttpOnly; SameSite=Lax{secure}"


def _go(h, where, *cookies):
    h.send_response(302)
    h.send_header("Location", where)
    h.send_header("Cache-Control", "no-store")
    h.send_header("Referrer-Policy", "no-referrer")
    for c in cookies:
        h.send_header("Set-Cookie", c)
    h.send_header("Content-Length", "0")
    h.end_headers()
    return True


def _oauth(h, cfg, rel):
    """api/oauth/me · api/oauth/<provider>/start · api/oauth/<provider>/callback (11_oauth)."""
    if rel == "api/oauth/me":
        return _json(h, 200, {"on": O.on(), "id": O.identity(_jar(h, "rcai_id"))})
    m = rel[len("api/oauth/"):].split("/")
    if len(m) != 2 or m[0] not in O.PROVIDERS or m[1] not in ("start", "callback"):
        return _json(h, 404, {"error": "not found"})
    name, path = m[0], f"{C.MOUNT}/api/oauth"
    if m[1] == "start":
        got = O.start(h, name)
        if not got:
            return _json(h, 503, {"error": "That sign-in is not switched on yet."})
        return _go(h, got[0], _oa_cookie("rcai_oa", got[1], 600, path))
    tok, why = O.callback(h, name, h.path.partition("?")[2], _jar(h, "rcai_oa"), cfg)
    A.log(f"{name}:{'ok' if tok else 'no'}", bool(tok), _ip(h), "oauth")
    gone = _oa_cookie("rcai_oa", "", 0, path)
    if not tok:
        return _go(h, f"{C.MOUNT}/?oa={urllib.parse.quote(why)}#signup", gone)
    return _go(h, f"{C.MOUNT}/#signup", gone, _oa_cookie("rcai_id", tok, O.ID_MIN * 60, C.MOUNT))


def _file(h, rel):
    f = (C.WEB / (rel or "index.html")).resolve()
    if C.WEB.resolve() not in f.parents or not f.is_file():
        return _json(h, 404, {"error": "not found"})
    return _send(h, 200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                 cache="no-cache" if f.suffix == ".html" or not os.environ.get("PORT") else "public, max-age=3600")


def handle(h, method):
    path = h.path.split("?", 1)[0].split("#", 1)[0]
    if path != C.MOUNT and not path.startswith(C.MOUNT + "/"):
        return False
    if path == C.MOUNT:                                   # relative links need the trailing slash
        h.send_response(301)
        h.send_header("Location", C.MOUNT + "/")
        h.send_header("Content-Length", "0")
        h.end_headers()
        return True
    rel = path[len(C.MOUNT) + 1:]
    cfg = _cfg()
    if rel.startswith("api/") and not cfg["hub_json"] and not cfg["hub"].exists():
        return _json(h, 503, {"error": "The portal is being set up. Write to customaimodels@gmail.com."})
    if method == "GET":
        if rel == "api/health":
            return _json(h, 200, {"ok": True})
        if rel.startswith("api/oauth/"):
            return _oauth(h, cfg, rel)
        if rel == "api/door":                             # src_follow_up: a door tapped in the sign-up email
            return _door(h)
        if rel == "api/me":
            email = _email(h)
            v = R.view(R.load(cfg), cfg, email) if email else None
            if not v:
                return _json(h, 401, {"in": False})
            return _json(h, 200, {"in": True, "stages": R.stages(), "own_pw": U.has_own(email),
                                  "pw_on": U.store() is not None,
                                  "epoch": cfg.get("state_epoch", "1"), "wait_until": I.until(cfg, email), **v})
        if rel == "api/master.csv":
            email = _email(h)
            if not email or email not in cfg["owners"]:
                return _json(h, 403, {"error": "owners only"})
            h.send_response(200)
            body = U.master_csv(cfg).encode()
            for k, val in (("Content-Type", "text/csv; charset=utf-8"), ("Cache-Control", "no-store"),
                           ("Content-Disposition", 'attachment; filename="R-CAI_MASTER.csv"'), ("Content-Length", str(len(body)))):
                h.send_header(k, val)
            h.end_headers()
            h.wfile.write(body)
            return True
        if rel.startswith("api/handbook/"):
            pid, email = rel[len("api/handbook/"):], _email(h)
            v = R.view(R.load(cfg), cfg, email) if email else None
            if not v or not any(c["id"] == pid and c.get("handbook") for c in v["projects"]):
                return _json(h, 404, {"error": "not found"})
            pdf = R.handbook_bytes(cfg, pid)
            if not pdf:
                return _json(h, 404, {"error": "not found"})
            h.send_response(200)
            for k, val in (("Content-Type", "application/pdf"), ("Cache-Control", "private, no-store"),
                           ("Content-Disposition", f'inline; filename="{pid}_HANDBOOK.pdf"'), ("Content-Length", str(len(pdf)))):
                h.send_header(k, val)
            h.end_headers()
            h.wfile.write(pdf)
            return True
        if rel.startswith(("api/visual/", "api/logo/")):
            kind, _, pid = rel[4:].partition("/")
            email = _email(h)
            v = R.view(R.load(cfg), cfg, email) if email else None
            if not v or not any(c["id"] == pid and c.get(kind) for c in v["projects"]):
                return _json(h, 404, {"error": "not found"})
            img, mime = (R.visual_bytes if kind == "visual" else R.logo_bytes)(cfg, pid)
            if not img:
                return _json(h, 404, {"error": "not found"})
            h.send_response(200)
            for k, val in (("Content-Type", mime), ("Cache-Control", "private, no-store"), ("Content-Length", str(len(img)))):
                h.send_header(k, val)
            h.end_headers()
            h.wfile.write(img)
            return True
        if rel == "api/admin/people":
            if not ADM.authed(h):
                return _json(h, 404, {"error": "not found"})
            return _json(h, 200, ADM.people(cfg))
        if rel == "api/activity":
            email = _email(h)
            if not email or email not in cfg["owners"]:
                return _json(h, 403, {"error": "owners only"})
            return _send(h, 200, T.report(T.load()).encode(), "text/plain; charset=utf-8")
        return _file(h, rel)
    if rel == "api/logout":
        return _json(h, 200, {"in": False}, _cookie("", 0))
    if rel == "api/admin/credit":
        if not ADM.authed(h):
            return _json(h, 404, {"error": "not found"})
        try:
            data = json.loads(h.rfile.read(min(int(h.headers.get("Content-Length", 0)), 2048)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return _json(h, 400, {"error": "bad request"})
        bal, why = ADM.add_credit(data.get("email"), data.get("amount"), data.get("note"))
        return _json(h, 400, {"error": why}) if bal is None else _json(h, 200, {"ok": True, "balance": bal})
    if rel not in ("api/login", "api/password", "api/scope", "api/event", "api/request", "api/signup", "api/reader"):
        return _json(h, 404, {"error": "not found"})
    try:
        n = min(int(h.headers.get("Content-Length", 0)), 16384 if rel in ("api/scope", "api/request") else 4096)
        data = json.loads(h.rfile.read(n) or b"{}")
    except (ValueError, json.JSONDecodeError):
        return _json(h, 400, {"error": "bad request"})
    if rel == "api/scope":
        return _scope(h, cfg, data)
    if rel == "api/event":
        return _event(h, cfg, data)
    if rel == "api/request":
        return _request(h, cfg, data)
    if rel == "api/reader":  # 2026-10-20: the article question card (src_articles/02_js/04_reader.js), no login
        return _reader(h, cfg, data)
    if rel == "api/signup":  # reopened 2026-10-18 behind Google/Microsoft only (11_oauth); the bare form stays shut
        return _signup(h, cfg, data)
    ip = _ip(h)
    if A.locked(cfg, ip):
        return _json(h, 429, {"error": "Too many tries. Wait a few minutes."})
    if rel == "api/password":
        return _password(h, cfg, ip, data)
    email = str(data.get("email", ""))[:120]
    ok = A.check_code(cfg, ip, str(data.get("code", ""))[:128], email)
    v = R.view(R.load(cfg), cfg, email) if ok else None
    A.log(email, bool(v), ip)
    if not v:
        return _json(h, 401, {"error": "That email and code word don't open a hub."})
    return _json(h, 200, {"in": True}, _cookie(A.issue(cfg, email), cfg["session_hours"] * 3600))


def _password(h, cfg, ip, data):
    """Signed in + the current password (or the shared code word) → the next pw_N column. Every other session ends."""
    email = _email(h)
    if not email:
        return _json(h, 401, {"error": "Sign in again."})
    if U.store() is None:
        return _json(h, 503, {"error": "Password changes switch on soon. Write to customaimodels@gmail.com."})
    cur, new = str(data.get("current", ""))[:128], str(data.get("new", ""))[:200]
    if not A.check_code(cfg, ip, cur, email):
        A.log(email, False, ip, "password")
        return _json(h, 403, {"error": "Your current password isn't right."})
    why = U.problem(new, cur)
    if why:
        return _json(h, 400, {"error": why})
    n = U.change(email, new)
    A.log(email, True, ip, f"password v{n}")
    return _json(h, 200, {"ok": True, "version": n}, _cookie(A.issue(cfg, email), cfg["session_hours"] * 3600))


def _scope(h, cfg, data):
    """Signed in, and only a scope this person can see: check (on Save) or review (on Review and send)."""
    email = _email(h)
    v = R.view(R.load(cfg), cfg, email) if email else None
    if not v:
        return _json(h, 401, {"error": "Sign in again."})
    try:
        p = v["projects"][int(data.get("i", -1))]
    except (ValueError, IndexError, TypeError):
        p = None
    if not p or not p.get("scope") or not isinstance(data.get("notes"), dict):
        return _json(h, 400, {"error": "bad request"})
    if data.get("stage") == "review":
        return _json(h, 200, V.review(cfg, p["scope"], data["notes"]))
    return _json(h, 200, V.check(cfg, p["scope"], data["notes"], min(int(data.get("tries", 0) or 0), 2)))


def _event(h, cfg, data):
    """Signed in, a project this person can see that carries a Phase 2, and an act from 07_activity.ACTS."""
    email = _email(h)
    v = R.view(R.load(cfg), cfg, email) if email else None
    if not v:
        return _json(h, 401, {"error": "Sign in again."})
    try:
        p = v["projects"][int(data.get("i", -1))]
    except (ValueError, IndexError, TypeError):
        p = None
    if not p or not p.get("scope") or not T.record(cfg, email, p, str(data.get("act", ""))[:20], data, v.get("name")):
        return _json(h, 400, {"error": "bad request"})
    return _json(h, 200, {"ok": True})


def _request(h, cfg, data):
    """Signed in; a kind from 08_inbox.KINDS; a project only if this person can see it. Inside their 24 h → 429."""
    email = _email(h)
    v = R.view(R.load(cfg), cfg, email) if email else None
    if not v:
        return _json(h, 401, {"error": "Sign in again."})
    kind, text = str(data.get("kind", ""))[:20], str(data.get("text", "")).strip()[:12000]
    proj = str(data.get("project", ""))[:120]
    if proj and not any(proj in (p.get("code"), p.get("name")) for p in v["projects"]):
        proj = ""
    if kind not in I.KINDS or kind == "signup" or not text:
        return _json(h, 400, {"error": "Write something first."})
    db = R.load(cfg)
    person = R.person_by_email(db, email) or {}
    card = next((p for p in v["projects"] if proj and proj in (p.get("code"), p.get("name"))), {})
    meta = {"client_id": person.get("company") or ("owner" if v.get("owner") else ""), "company": card.get("company") or v.get("company"),
            "project_id": card.get("id", ""), "project_name": card.get("name", "")}
    meta.update({k: data[k] for k in ("total", "deposit") if isinstance(data.get(k), (int, float))})
    ok, until = I.put(cfg, email, kind, text, proj, v.get("full") or v.get("name"), meta)
    if not ok:
        return _json(h, 429, {"error": "We have your last request. We write back within 24 hours.", "until": until})
    return _json(h, 200, {"ok": True, "until": until})


def _door(h):
    """Signed link only (src_follow_up.link). Logs {at,email,door} to <inbox>/doors.jsonl + RCAI_DOOR, then 302s
    to the public page with utm tags (the beacon counts it on WEB). A bad signature just goes to /articles/."""
    F = importlib.import_module("src_follow_up.follow")
    href, row = F.open_(h.path.split("?", 1)[1] if "?" in h.path else "")
    if not row:
        return _go(h, "/articles/")
    line = json.dumps(row, ensure_ascii=False)
    print("RCAI_DOOR " + line, flush=True)
    try:
        f = I.folder()
        f.mkdir(parents=True, exist_ok=True)
        with (f / "doors.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    return _go(h, href)


_SIGNUPS = {}
_READERS = {}
_EMAIL = __import__("re").compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[a-z]{2,24}$", __import__("re").I)


def _reader(h, cfg, data):
    """The article card (2026-10-20, v2): {name, company, scale, answer, email, consent, page, src, vid}.
    Same shape as the sign-up (name · company · team size · their words). Saved to 08_inbox kind=reader + admin mail.
    vid = the visitor beacon's anonymous id, so __Ysrc/11_inbound.py can join what they read before they wrote.
    Consent tick required (we only write back to people who asked). 3 per IP a day; same email waits 24 h."""
    ip, day = _ip(h), time.strftime("%Y-%m-%d")
    f = {k: str(data.get(k, "")).strip()[:1200 if k == "answer" else 160]
         for k in ("email", "answer", "page", "src", "name", "company", "scale", "vid", "frame")}
    if str(data.get("hp", "")).strip():                 # honeypot: bots fill it, people never see it
        return _json(h, 200, {"ok": True})
    if len(f["name"]) < 2:
        return _json(h, 400, {"error": "Your name, please."})
    if not _EMAIL.match(f["email"]):
        return _json(h, 400, {"error": "That email doesn't look right."})
    if len(f["answer"]) < 3:
        return _json(h, 400, {"error": "One line is enough. What would you fix first?"})
    if data.get("consent") is not True:
        return _json(h, 400, {"error": "Tick the box so we can write back."})
    if not f["page"].startswith("/articles/"):
        f["page"] = "/articles/"
    if not __import__("re").fullmatch(r"[a-z0-9]{4,16}", f["vid"]):
        f["vid"] = ""
    if _READERS.get((ip, day), 0) >= 3:
        return _json(h, 429, {"error": "We have it. We write back within 24 hours."})
    text = (f"From the article: https://customaimodels.com{f['page']}\nCame from: {f['src'] or 'direct'}\n"
            f"Name: {f['name']}\nCompany: {f['company'] or '-'}\nTeam size: {f['scale'] or '-'}\nEmail: {f['email']}\n"
            f"Consent to reply: yes\n\nTheir data problem:\n{f['answer']}")
    ok, until = I.put(cfg, f["email"], "reader", text, "", f["name"],
                      {"client_id": "reader", "page": f["page"], "src": f["src"], "company": f["company"],
                       "scale": f["scale"], "vid": f["vid"], "frame": f["frame"]})
    if not ok:
        return _json(h, 429, {"error": "We have it. We write back within 24 hours.", "until": until})
    _READERS[(ip, day)] = _READERS.get((ip, day), 0) + 1
    return _json(h, 200, {"ok": True})


def _signup(h, cfg, data):
    who = O.identity(_jar(h, "rcai_id"))
    if not who:
        return _json(h, 403, {"error": "Continue with Google or Microsoft first."})
    ip, day = _ip(h), time.strftime("%Y-%m-%d")
    n = _SIGNUPS.get((ip, day), 0)
    f = {k: str(data.get(k, "")).strip()[:2000 if k == "need" else 120] for k in ("company", "scale", "need")}
    f.update(name=who["name"], email=who["email"])
    if not f["need"]:
        return _json(h, 400, {"error": "Tell us what you need, please."})
    if n >= 3:
        return _json(h, 429, {"error": "We have your request. We write back within 24 hours."})
    text = (f"Name: {f['name']}\nCompany: {f['company']}\nTeam size: {f['scale']}\nEmail: {f['email']}\n"
            f"Verified by: {who['provider']}\n\nWhat we need:\n{f['need']}")
    ok, until = I.put(cfg, f["email"], "signup", text, "", f["name"], {"client_id": "new", "company": f["company"], "scale": f["scale"], "provider": who["provider"]})
    if not ok:
        return _json(h, 429, {"error": "We have your request. We write back within 24 hours.", "until": until})
    _SIGNUPS[(ip, day)] = n + 1
    N.received({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "email": f["email"], "person": f["name"], "need": f["need"]}, cfg)  # their "we have it" (09_notify)
    return _json(h, 200, {"ok": True, "until": until})
