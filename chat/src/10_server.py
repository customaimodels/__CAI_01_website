"""The HTTP door the landing page talks to.
POST /api/chat {session_id?, message} ──▶ {reply, session_id, live, mode, sources[], lead_captured?}
GET  /api/chat/status                 ──▶ {ok, model, live, mode, docs}

Hosted (Railway): CAI_SITE=<dir> also serves the landing page from that dir on the same origin,
and HOST / PORT come from the environment. mode = "model" (a model answers) or "record"
(no model on this host: the best matching corpus passage, verbatim).
"""
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from pathlib import Path

C = import_module("src.02_config")
X = import_module("src.04_index")
L = import_module("src.06_llm")
H = import_module("src.09_chat")

SITE = Path(os.environ["CAI_SITE"]).resolve() if os.environ.get("CAI_SITE") else None


def _origins():
    return {o.strip() for o in C.get("allow_origins", "").split(",") if o.strip()}


def _mode():
    return "model" if L.up() else ("record" if X.corpus() else "script")


class Door(BaseHTTPRequestHandler):
    server_version = "cai-chat"

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        origin = self.headers.get("Origin", "")
        if origin in _origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self):
        """The landing page, only when CAI_SITE is set. Nothing outside SITE is ever served."""
        rel = self.path.split("?", 1)[0].split("#", 1)[0].lstrip("/") or "index.html"
        f = (SITE / rel).resolve()
        if f.is_dir():
            f = f / "index.html"
        if SITE not in f.parents or not f.is_file():
            return self._send(404, {"error": "not_found"})
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache" if f.suffix == ".html" else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        origin = self.headers.get("Origin", "")
        if origin in _origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?", 1)[0].rstrip("/")
        if p == "/api/chat/status":
            mode = _mode()
            return self._send(200, {"ok": True, "live": mode != "script", "mode": mode, "docs": len(X.corpus()),
                                    "model": {"claude_cli": "Claude", "anthropic_api": "Claude",
                                              "ollama": "Local"}.get(L.live_road(), "the record")})
        if p == "/healthz":
            return self._send(200, {"ok": True})
        if SITE:
            return self._file()
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/chat":
            return self._send(404, {"error": "not_found"})
        try:
            n = min(int(self.headers.get("Content-Length", 0)), 16_000)
            data = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "bad_json"})
        out = H.turn(data.get("session_id"), data.get("message", ""))
        out["mode"] = "model" if out.get("live") else _mode()
        self._send(200, out)

    def log_message(self, fmt, *args):
        pass  # requests are not logged: visitors' words stay out of the terminal


def serve(port=None):
    host = os.environ.get("HOST") or ("0.0.0.0" if os.environ.get("PORT") else C.get("host", "127.0.0.1"))
    port = int(os.environ.get("PORT") or port or C.get("port", 8190, int))
    with ThreadingHTTPServer((host, port), Door) as srv:
        print(f"▸ CAI chat  http://{host}:{port}/api/chat   road {L.live_road() or '-'} · mode {_mode()}"
              f"{'   · site ' + str(SITE) if SITE else ''}   ctrl-c stops", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
