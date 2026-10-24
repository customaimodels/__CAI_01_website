"""/brain/mcp/<secret> (2026-10-24): a REMOTE MCP server for Claude (Settings → Connectors → Add custom connector).
No UI, no login: the long random secret in the URL is the lock. SEND ONLY (v2, 2026-10-24, replaces save_thought):
one tool, send(to, kind, title, body) → a .txt + .yml pair written STRAIGHT into _txt_claude (CHANGED 2026-10-24 03:30:
INBOX below = Drive's My Mac > Documents > _txt_claude, the backup of Pythonista's iCloud _txt_claude), so Drive sync
lands it on the Mac by itself. No inbox folder, no launchd mover (__Ysrc/18_inbox_mover.py kept as an unused fallback).
A taken name (same minute + title) gets -2, -3 … : nothing is ever overwritten.

Official MCP SDK (mcp==2.3.0, MCPServer), Streamable HTTP, stateless + JSON responses: every call is one POST → one JSON.
The SDK's ASGI app runs on ONE background event loop inside the site's own stdlib process; this module bridges each
POST from the http.server thread into it. Nothing else on customaimodels.com changes.

    POST /brain/mcp/<secret>      MCP (initialize · tools/list · tools/call …)
    GET | DELETE                  405 (stateless: no stream, no session to end)
    wrong / missing secret        404, and 10 misses = that IP locked 10 min

Secrets: env BRAIN_MCP_SECRET_SHA256 (Railway) or dta/_1_processed/brain/secrets.json (local, 0600).
The plain secret is never stored next to it: `run.py --brain-mcp-secret` makes one, keeps the hash, and puts the full
connector URL on his clipboard + dta/_1_processed/brain/connector_url.txt (0600). New secret = the old URL is dead.
No mcp package (local py3.9 preview) = 503 here, the rest of /brain unaffected.
"""
import asyncio
import hashlib
import hmac
import importlib
import json
import os
import re
import secrets
import threading
import time
import unicodedata

B = importlib.import_module("src_brain.brain")
PREFIX = B.MOUNT + "/mcp/"
MAX_BYTES, MAX_MISS, LOCK_MIN, TIMEOUT = 64_000, 10, 10, 60
HOSTS = ["customaimodels.com", "127.0.0.1:*", "localhost:*"]
_RT, _MISS, _BOOT = {}, {}, threading.Lock()


def _hash():
    return B._env("BRAIN_MCP_SECRET_SHA256").lower()


def new_secret():
    """A fresh 43-char secret. Returns (secret, its sha256). The caller keeps the hash; the secret goes to him only."""
    s = secrets.token_urlsafe(32)
    return s, hashlib.sha256(s.encode()).hexdigest()


def _match(path):
    want = _hash()
    got = path[len(PREFIX):].strip("/") if path.startswith(PREFIX) else ""
    if len(want) != 64 or len(got) < 32 or "/" in got:
        return False
    return hmac.compare_digest(hashlib.sha256(got.encode()).hexdigest(), want)


def _missed(ip):
    now = time.time()
    _MISS[ip] = [t for t in _MISS.get(ip, []) if now - t < LOCK_MIN * 60]
    return len(_MISS[ip]) >= MAX_MISS


# -- the MCP server (official SDK) ----------------------------------------------------------------------------
def build():
    """The MCPServer with its one tool. Separate from the runtime so the test can call it directly."""
    from typing import TypedDict

    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations

    class Sent(TypedDict):
        id: str
        txt: str
        yml: str
        link: str

    srv = MCPServer("cai-brain", title="CAI Brain",
                    instructions=("Send a task, note or thought to one of Yeriko's agents. SEND ONLY: nothing is read back. "
                                  "to = MandaMas | Y_MandaMas | Y_Memory. One call per message."),
                    website_url="https://customaimodels.com", version="2.0")

    @srv.tool(title="Send to an agent",
              annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def send(to: str, kind: str, title: str, body: str) -> Sent:
        """Send one message to an agent's inbox. to: MandaMas | Y_MandaMas | Y_Memory. kind: task | note | thought.
        title: short, 60 chars max. body: free text. Writes a .txt + .yml pair into the agents' _txt_claude folder."""
        try:
            p = pair(to, kind, title, body)
        except ValueError as e:
            raise ToolError(str(e))
        try:
            p = await asyncio.to_thread(_free, p)
        except RuntimeError as e:
            raise ToolError(f"Not sent: {e}")
        try:                                             # TXT first, then YML: the yml is the "ready" signal
            t = await asyncio.to_thread(B.upload, p["txt_name"], p["txt"], INBOX)
            await asyncio.to_thread(B.upload, p["yml_name"], p["yml"], INBOX, "text/yaml")
        except RuntimeError as e:                        # "Drive not connected" · "Drive said 401" … short, no secrets
            raise ToolError(f"Not sent: {e}")
        return {"id": p["id"], "txt": p["txt_name"], "yml": p["yml_name"], "link": t["link"]}

    return srv


# -- the message pair (pure: the test checks it without Drive) ---------------------------------------------------
INBOX = os.environ.get("BRAIN_TXT_CLAUDE_FOLDER_ID") or "1PjylRytaYdHPR1ApicibAq6LtmQFNsF1"   # _txt_claude (his folder)
TO = ("MandaMas", "Y_MandaMas", "Y_Memory")
KINDS = ("task", "note", "thought")


def _slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower())
    return s.strip("-")[:48].strip("-") or "untitled"


def pair(to, kind, title, body, now=None, suffix=None):
    """→ {id, txt_name, txt, yml_name, yml}. Raises ValueError with a short reason; nothing else is accepted."""
    to, kind, title, body = (to or "").strip(), (kind or "").strip().lower(), " ".join((title or "").split()), body or ""
    if to not in TO:
        raise ValueError(f"to must be one of {', '.join(TO)}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if not title or len(title) > 60:
        raise ValueError("title: 1 to 60 characters")
    if not body.strip():
        raise ValueError("empty body: nothing sent")
    if len(body.encode("utf-8")) > B.MAX_BYTES:
        raise ValueError(f"body too long: keep it under {B.MAX_BYTES // 1000} KB")
    now = (now or B.datetime.now(B.TZ)).replace(microsecond=0)
    stamp = now.strftime("%Y%m%d-%H%M")
    mid = f"{stamp}-{suffix or secrets.token_hex(2)}"
    base = f"{stamp}_to-{to}_{kind}_{_slug(title)}"
    txt = f"TO: {to} | KIND: {kind} | {now.strftime('%Y-%m-%d %H:%M')}\nTITLE: {title}\n---\n{body.rstrip()}\n"
    yml = "".join(f"{k}: {v}\n" for k, v in (
        ("id", mid), ("created", now.isoformat()), ("to", to), ("from", "claude"), ("kind", kind),
        ("title", json.dumps(title, ensure_ascii=False)), ("status", "new"), ("txt", base + ".txt")))
    return {"id": mid, "txt_name": base + ".txt", "txt": txt, "yml_name": base + ".yml", "yml": yml}


def _free(p):
    """Same pair, renamed -2, -3 … until neither the .txt nor the .yml name is taken in _txt_claude."""
    base, n = p["txt_name"][:-4], 1
    while True:
        b = base if n == 1 else f"{base}-{n}"
        if not (B.exists(b + ".txt", INBOX) or B.exists(b + ".yml", INBOX)):
            break
        n += 1
        if n > 20:
            raise RuntimeError("name taken 20 times")
    if b != base:
        p = dict(p, txt_name=b + ".txt", yml_name=b + ".yml", yml=p["yml"].replace(f"txt: {base}.txt", f"txt: {b}.txt"))
    return p


def _runtime():
    """One loop thread + the SDK's Starlette app with its lifespan started. Built on the first call, cached after."""
    with _BOOT:
        if _RT.get("app"):
            return _RT
        from mcp.server.transport_security import TransportSecuritySettings
        app = build().streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True,
                                          max_request_body_size=MAX_BYTES,
                                          transport_security=TransportSecuritySettings(allowed_hosts=HOSTS))
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever, name="brain-mcp", daemon=True).start()
        ready = asyncio.run_coroutine_threadsafe(_lifespan(app), loop).result(TIMEOUT)
        if ready != "lifespan.startup.complete":
            raise RuntimeError("MCP server did not start")
        _RT.update(app=app, loop=loop)
        return _RT


async def _lifespan(app):
    """Start the app's lifespan (the SDK's session manager) and keep it open for the life of the process."""
    done, asked = asyncio.get_running_loop().create_future(), {"startup": False}

    async def receive():
        if not asked["startup"]:
            asked["startup"] = True
            return {"type": "lifespan.startup"}
        return await asyncio.Future()                    # never a shutdown: the process owns the loop

    async def send(msg):
        if msg["type"].startswith("lifespan.startup") and not done.done():
            done.set_result(msg["type"])

    asyncio.get_running_loop().create_task(app({"type": "lifespan", "asgi": {"version": "3.0"}, "state": {}}, receive, send))
    return await done


async def _call(app, scope, body):
    out = {"status": 500, "headers": [], "body": b""}
    fed = {"done": False}

    async def receive():
        if not fed["done"]:
            fed["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await asyncio.Future()                    # never a disconnect: the reply is one JSON body

    async def send(msg):
        if msg["type"] == "http.response.start":
            out["status"], out["headers"] = msg["status"], msg.get("headers", [])
        elif msg["type"] == "http.response.body":
            out["body"] += msg.get("body", b"")

    await app(scope, receive, send)
    return out


def _scope(h, ip):
    host = h.headers.get("Host", "")
    return {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
            "scheme": "https" if B.os.environ.get("PORT") else "http", "path": "/mcp", "raw_path": b"/mcp",
            "query_string": b"", "root_path": "", "client": (ip, 0), "server": (host.split(":")[0] or "localhost", 443),
            "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in h.headers.items()], "state": {}}


def handle(h, method):
    path = h.path.split("?", 1)[0]
    ip = B._ip(h)
    if _missed(ip):
        return B._json(h, 429, {"error": "busy"})
    if not _match(path):
        _MISS.setdefault(ip, []).append(time.time())
        return B._send(h, 404, "Not found", "text/plain")
    if method != "POST":
        return B._send(h, 405, "", "text/plain", extra=(("Allow", "POST"),))
    n = int(h.headers.get("Content-Length") or 0)
    if n > MAX_BYTES:
        return B._json(h, 413, {"error": "too long"})
    body = h.rfile.read(n)
    try:
        rt = _runtime()
    except ImportError:
        return B._json(h, 503, {"error": "mcp not installed on this host"})
    except Exception:
        return B._json(h, 503, {"error": "connector starting failed"})
    try:
        out = asyncio.run_coroutine_threadsafe(_call(rt["app"], _scope(h, ip), body), rt["loop"]).result(TIMEOUT)
    except Exception:
        return B._json(h, 504, {"error": "timed out"})
    h.send_response(out["status"])
    skip = {b"content-length", b"connection", b"transfer-encoding"}
    for k, v in out["headers"]:
        if k.lower() not in skip:
            h.send_header(k.decode("latin-1"), v.decode("latin-1"))
    h.send_header("Content-Length", str(len(out["body"])))
    h.send_header("Cache-Control", "no-store")
    h.send_header("X-Robots-Tag", "noindex, nofollow")
    h.end_headers()
    h.wfile.write(out["body"])
    return True
