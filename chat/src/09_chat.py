"""One turn: session ──▶ answer ──▶ lead check ──▶ payload the page renders."""
import threading
import uuid
from importlib import import_module

C = import_module("src.02_config")
A = import_module("src.07_answer")
D = import_module("src.08_leads")

_SESSIONS, _LOCK = {}, threading.Lock()
_MAX_SESSIONS = 500


def _session(sid):
    with _LOCK:
        if sid and sid in _SESSIONS:
            return sid, _SESSIONS[sid]
        if len(_SESSIONS) >= _MAX_SESSIONS:
            _SESSIONS.pop(next(iter(_SESSIONS)))
        sid = uuid.uuid4().hex
        _SESSIONS[sid] = {"messages": [], "lead": False}
        return sid, _SESSIONS[sid]


def turn(session_id, message):
    message = (message or "").strip()[: C.get("max_message_chars", 1200, int)]
    if not message:
        return {"reply": "Ask me anything about what Custom AI Models can build for you.",
                "session_id": session_id or "", "error": "empty_message"}
    sid, s = _session(session_id)
    reply, chunks, live = A.answer(s["messages"], message)
    keep = C.get("history_max_turns", 10, int) * 2
    s["messages"] = (s["messages"] + [{"role": "user", "content": message},
                                      {"role": "assistant", "content": reply}])[-keep:]
    out = {"reply": reply, "session_id": sid, "live": live,
           "sources": list(dict.fromkeys(c["title"] for c in chunks))}
    lead = None if s["lead"] else D.parse(message)
    if lead:
        D.save(sid, lead)
        s["lead"] = out["lead_captured"] = True
    return out
