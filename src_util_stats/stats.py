"""VISITORS: first-party visit log for the public pages (2026-10-18). Stdlib only, no third party sees a visit.

    GET  /cai-beacon.js        the beacon, ~1 KB. --bundle puts <script defer src="/cai-beacon.js"> in every PUBLIC page
                               (site/, src_articles/, src_resume/); the vault, R-CAI and /recruiter never carry it.
    POST /api/hit              {e: view|click|leave, vid, sid, n, p, r, src, us, um, uc, w, sd, et, t, h} -> 204
    GET  /api/stats/hits?since=<epoch>   Authorization: Bearer <key>  -> {ok, rows, now}   (SCRN pulls this; 404 without the key)

What one row holds (and what it never holds):
    ts · e · vid (random id in the visitor's localStorage) · sid (sessionStorage) · n (1 = first visit on that browser)
    p (path) · ref (referrer HOST only) · src / utm_* · cc + city + rg (Cloudflare's headers, when present)
    dev · br · os (from the user agent) · sd (scroll %) · et (engaged seconds) · t + h (what was clicked)
    NEVER: the IP, the full user agent, the full referrer URL, a name or an email. Do Not Track / GPC = nothing is sent.

Not counted: his own visits (yvault cookie, or ?cai_me=1 once per browser), bots (UA list + navigator.webdriver),
private paths (/y-vault /r-cai /recruiter /api), anything over 4 KB, more than 120 hits a minute from one address.

Where rows land: <STATS_DIR>/hits.jsonl (a Railway volume) or, locally, dta/_0_raw/stats/hits.jsonl; hosted they are
also printed as `CAI_HIT {...}` so Railway's log keeps them if the folder forgets on deploy. SCRN keeps the archive.
The key: only its sha256, Railway STATS_KEY_SHA256 (local dta/_1_processed/stats/key.sha256). None set = no read door.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ("/y-vault", "/r-cai", "/recruiter", "/api", "/studio")
EVENTS = {"view", "click", "leave"}
BOTS = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|quora|pinterest|vkshare|whatsapp|"
                  r"lighthouse|headless|phantom|python|curl|wget|httpclient|go-http|okhttp|axios|node-fetch|scrapy", re.I)
_LOCK, _RATE = threading.Lock(), {}

BEACON = r"""(()=>{try{const L=localStorage,S=sessionStorage,q=new URLSearchParams(location.search);
if(q.get("cai_me")==="1")L.cai_me="1";
if(L.cai_me||navigator.webdriver||navigator.globalPrivacyControl||navigator.doNotTrack==="1")return;
let n=0;if(!L.cai_v){L.cai_v=Math.random().toString(36).slice(2,14);n=1}
const sid=S.cai_s||(S.cai_s=Math.random().toString(36).slice(2,12));
const send=(e,x)=>{const b=JSON.stringify(Object.assign({e,vid:L.cai_v,sid,n,p:location.pathname,r:document.referrer,
src:q.get("src")||"",us:q.get("utm_source")||"",um:q.get("utm_medium")||"",uc:q.get("utm_campaign")||"",w:innerWidth},x||{}));
if(navigator.sendBeacon)navigator.sendBeacon("/api/hit",new Blob([b],{type:"text/plain"}));
else fetch("/api/hit",{method:"POST",body:b,keepalive:true})};
send("view");n=0;
let sd=0,et=0,t0=document.hidden?0:Date.now();
addEventListener("scroll",()=>{const h=document.documentElement,d=Math.round((scrollY+innerHeight)/h.scrollHeight*100);if(d>sd)sd=Math.min(100,d)},{passive:true});
document.addEventListener("click",ev=>{const a=ev.target.closest&&ev.target.closest("a,button");if(!a)return;
send("click",{t:(a.getAttribute("aria-label")||a.textContent||"").replace(/\s+/g," ").trim().slice(0,60),h:(a.getAttribute("href")||"").slice(0,200)})},true);
const leave=()=>{if(t0){et+=Date.now()-t0;t0=0}send("leave",{sd,et:Math.round(et/1000)})};
document.addEventListener("visibilitychange",()=>{if(document.hidden)leave();else t0=Date.now()});
addEventListener("pagehide",leave)}catch(e){}})();
"""


def _store() -> Path:
    d = Path(os.environ["STATS_DIR"]) if os.environ.get("STATS_DIR") else ROOT / "dta" / "_0_raw" / "stats"
    d.mkdir(parents=True, exist_ok=True)
    return d / "hits.jsonl"


def _key_hash() -> str:
    v = os.environ.get("STATS_KEY_SHA256", "").strip()
    if not v:
        f = ROOT / "dta" / "_1_processed" / "stats" / "key.sha256"
        v = f.read_text(encoding="utf-8").strip() if f.is_file() else ""
    return v if re.fullmatch(r"[0-9a-f]{64}", v) else ""


def new_key() -> str:
    """A fresh read key: its sha256 goes to dta/_1_processed/stats/key.sha256 (and Railway); the key itself
    is returned once, for SCRN's local key file. Never printed by the caller."""
    k = secrets.token_urlsafe(32)
    f = ROOT / "dta" / "_1_processed" / "stats" / "key.sha256"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(hashlib.sha256(k.encode()).hexdigest() + "\n", encoding="utf-8")
    os.chmod(f, 0o600)
    return k


def _send(h, code, body=b"", ctype="text/plain", extra=()):
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(body)))
    for k, v in extra:
        h.send_header(k, v)
    h.end_headers()
    if body:
        h.wfile.write(body)


def _ip(h) -> str:
    return (h.headers.get("CF-Connecting-IP") or h.headers.get("X-Forwarded-For", "").split(",")[0]
            or h.client_address[0]).strip()


def _limited(ip: str) -> bool:
    now = int(time.time() // 60)
    tag = hashlib.sha256(ip.encode()).hexdigest()[:16]   # the address is never kept, not even in memory as itself
    with _LOCK:
        if len(_RATE) > 5000:
            _RATE.clear()
        k = (tag, now)
        _RATE[k] = _RATE.get(k, 0) + 1
        return _RATE[k] > 120


def device(ua: str, width: int) -> tuple:
    u = ua.lower()
    dev = "tablet" if ("ipad" in u or "tablet" in u or ("android" in u and "mobile" not in u)) else \
          "mobile" if ("mobi" in u or "iphone" in u or (width and width < 700)) else "desktop"
    br = "Edge" if "edg/" in u else "Chrome" if ("chrome/" in u or "crios" in u) else "Firefox" if ("firefox" in u or "fxios" in u) \
        else "Safari" if "safari" in u else "LinkedIn app" if "linkedinapp" in u else "Other"
    if "linkedinapp" in u:
        br = "LinkedIn app"
    os_ = "iOS" if ("iphone" in u or "ipad" in u) else "Android" if "android" in u else "macOS" if "mac os" in u \
        else "Windows" if "windows" in u else "Linux" if "linux" in u else "Other"
    return dev, br, os_


def _clip(v, n) -> str:
    return re.sub(r"[\x00-\x1f]", " ", str(v or ""))[:n]


def row(data: dict, headers, host: str = "") -> dict | None:
    """One beacon body -> one stored row, or None when it must not be kept."""
    e, p = data.get("e"), _clip(data.get("p"), 200)
    if e not in EVENTS or not p.startswith("/") or any(p == x or p.startswith(x + "/") for x in PRIVATE):
        return None
    vid, sid = _clip(data.get("vid"), 16), _clip(data.get("sid"), 16)
    if not re.fullmatch(r"[a-z0-9]{4,16}", vid) or not re.fullmatch(r"[a-z0-9]{4,16}", sid):
        return None
    ua = headers.get("User-Agent", "")
    if not ua or BOTS.search(ua):
        return None
    ref = re.sub(r"^https?://", "", _clip(data.get("r"), 300)).split("/", 1)[0].split(":", 1)[0].lower()
    if ref.startswith("www."):
        ref = ref[4:]
    if host and ref == host.split(":", 1)[0].lower().removeprefix("www."):
        ref = ""                                    # moving inside the site is not a source
    try:
        w = max(0, min(10000, int(data.get("w") or 0)))
    except (TypeError, ValueError):
        w = 0
    dev, br, os_ = device(ua, w)
    out = {"ts": int(time.time()), "e": e, "vid": vid, "sid": sid, "n": 1 if data.get("n") in (1, "1", True) else 0,
           "p": p, "ref": ref, "src": _clip(data.get("src"), 40), "us": _clip(data.get("us"), 40),
           "um": _clip(data.get("um"), 40), "uc": _clip(data.get("uc"), 60),
           "cc": _clip(headers.get("CF-IPCountry", ""), 2).upper(), "city": _clip(headers.get("cf-ipcity", ""), 40),
           "rg": _clip(headers.get("cf-region", ""), 40), "dev": dev, "br": br, "os": os_}
    if e == "leave":
        for k, top in (("sd", 100), ("et", 3600)):
            try:
                out[k] = max(0, min(top, int(data.get(k) or 0)))
            except (TypeError, ValueError):
                out[k] = 0
    if e == "click":
        out["t"], out["h"] = _clip(data.get("t"), 60), _clip(data.get("h"), 200)
    return out


def keep(r: dict) -> None:
    line = json.dumps(r, separators=(",", ":"))
    with _LOCK, _store().open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    if os.environ.get("PORT"):
        print("CAI_HIT " + line, flush=True)


def read(since: int = 0, limit: int = 20000) -> list:
    f = _store()
    if not f.exists():
        return []
    out = []
    with f.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ts", 0) > since:
                out.append(r)
    return out[-limit:]


def handle(h, method) -> bool:
    path = h.path.split("?", 1)[0]
    if method == "GET" and path == "/cai-beacon.js":
        _send(h, 200, BEACON.encode(), "text/javascript; charset=utf-8", (("Cache-Control", "public, max-age=3600"),))
        return True
    if method == "POST" and path == "/api/hit":
        try:
            n = int(h.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        body = h.rfile.read(n) if 0 < n <= 4096 else b""
        if n > 4096:
            h.rfile.read(n)
        if body and "yvault=" not in (h.headers.get("Cookie") or "") and not _limited(_ip(h)):
            try:
                r = row(json.loads(body.decode("utf-8", "replace")), h.headers, h.headers.get("Host", ""))
                if r:
                    keep(r)
            except (ValueError, AttributeError):
                pass
        _send(h, 204, extra=(("Cache-Control", "no-store"),))
        return True
    if method == "GET" and path == "/api/stats/hits":
        want = _key_hash()
        got = (h.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        if not want or not got or not hmac.compare_digest(hashlib.sha256(got.encode()).hexdigest(), want):
            _send(h, 404, b"not found")
            return True
        q = dict(x.split("=", 1) for x in (h.path.split("?", 1)[1] if "?" in h.path else "").split("&") if "=" in x)
        try:
            since = int(q.get("since", "0"))
        except ValueError:
            since = 0
        body = json.dumps({"ok": True, "rows": read(since), "now": int(time.time())}).encode()
        _send(h, 200, body, "application/json", (("Cache-Control", "no-store"), ("X-Robots-Tag", "noindex, nofollow")))
        return True
    return False


TAG = '<script defer src="/cai-beacon.js"></script>'


def tag_pages(bundle: Path) -> int:
    """--bundle: the beacon tag into every PUBLIC html page, once, right before </head>."""
    n = 0
    for top in ("site", "src_articles", "src_resume"):
        for f in (bundle / top).rglob("*.html"):
            s = f.read_text(encoding="utf-8")
            if TAG in s or "</head>" not in s:
                continue
            f.write_text(s.replace("</head>", TAG + "\n</head>", 1), encoding="utf-8")
            n += 1
    return n
