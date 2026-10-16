"""Roads to a model, tried in config order (`provider:`). Raises Unavailable; never guesses.

  claude_cli    the `claude` CLI already signed in on this Mac -- no key, no tools, ~600 tokens overhead
  anthropic_api the Messages API over plain HTTP -- needs ANTHROPIC_API_KEY (the road for a hosted site)
  ollama        local Ollama /api/chat -- free, slow (~30 s on llama3.2:3b), loose on grounding
"""
import json
import os
import shutil
import subprocess
from importlib import import_module
from pathlib import Path
from urllib import error, request

C = import_module("src.02_config")


class Unavailable(Exception):
    pass


def _split(messages):
    """[{role, content}] → (system text, one-shot transcript, chat turns for the API)."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] in ("user", "assistant")]
    if len(turns) == 1:
        transcript = turns[0]["content"]
    else:
        lines = [f"{'VISITOR' if m['role'] == 'user' else 'CAI'}: {m['content']}" for m in turns[:-1]]
        transcript = ("Conversation so far:\n" + "\n\n".join(lines) +
                      "\n\nThe visitor now says:\n" + turns[-1]["content"])
    return system, transcript, turns


# -- claude CLI ------------------------------------------------------------------------------------
def _claude_bin():
    for c in (shutil.which("claude"), Path.home() / ".local/bin/claude", "/opt/homebrew/bin/claude",
              "/usr/local/bin/claude"):
        if c and Path(c).exists():
            return str(c)
    return ""


def _ask_cli(messages):
    exe = _claude_bin()
    if not exe:
        raise Unavailable("claude CLI not found")
    system, transcript, _ = _split(messages)
    # Every flag keeps the call bare: no tools, no MCP, no memory, no CLAUDE.md riding along.
    cmd = [exe, "-p", "--model", C.get("cli_model", "haiku"), "--output-format", "json", "--tools", "",
           "--system-prompt", system, "--no-session-persistence", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "local", "--disable-slash-commands",
           "--exclude-dynamic-system-prompt-sections"]
    try:
        r = subprocess.run(cmd, input=transcript, capture_output=True, text=True,
                           timeout=C.get("timeout_seconds", 60, float), cwd=str(Path.home()))
    except subprocess.TimeoutExpired as e:
        raise Unavailable("claude CLI timed out") from e
    try:
        out = json.loads(r.stdout or "{}")
    except json.JSONDecodeError as e:
        raise Unavailable((r.stderr or "claude CLI gave no output")[:300]) from e
    text = out.get("result")
    if r.returncode != 0 or out.get("is_error") or not isinstance(text, str) or not text.strip():
        raise Unavailable(str(text or r.stderr or "claude CLI failed")[:300])
    return text.strip()


# -- Anthropic API ---------------------------------------------------------------------------------
def _ask_api(messages):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise Unavailable("ANTHROPIC_API_KEY not set")
    system, _, turns = _split(messages)
    # No temperature: claude-haiku-5-5 rejects it with a 400 ("deprecated for this model").
    body = {"model": C.get("api_model", "claude-haiku-5-5"), "max_tokens": 700,
            "system": system, "messages": turns}
    req = request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
                          {"Content-Type": "application/json", "x-api-key": key,
                           "anthropic-version": "2023-06-01"})
    try:
        with request.urlopen(req, timeout=C.get("timeout_seconds", 60, float)) as r:
            data = json.loads(r.read().decode())
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        raise Unavailable(str(e)) from e
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    if not text.strip():
        raise Unavailable("empty reply")
    return text.strip()


# -- Ollama ----------------------------------------------------------------------------------------
def _url(path):
    return C.get("base_url", "http://localhost:11434").rstrip("/") + path


def _ask_ollama(messages):
    body = {"model": C.get("model", "llama3.2:3b"), "messages": messages, "stream": False,
            "options": {"temperature": C.get("temperature", 0.1, float)}}
    req = request.Request(_url("/api/chat"), json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=C.get("ollama_timeout_seconds", 120, float)) as r:
            data = json.loads(r.read().decode())
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        raise Unavailable(str(e)) from e
    text = (data.get("message") or {}).get("content")
    if not isinstance(text, str) or not text.strip():
        raise Unavailable("empty reply")
    return text.strip()


def _ollama_up():
    try:
        with request.urlopen(_url("/api/tags"), timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


ROADS = {"claude_cli": (_ask_cli, lambda: bool(_claude_bin())),
         "anthropic_api": (_ask_api, lambda: bool(os.environ.get("ANTHROPIC_API_KEY"))),
         "ollama": (_ask_ollama, _ollama_up)}


def providers():
    names = [p.strip() for p in C.get("provider", "claude_cli, ollama").split(",") if p.strip()]
    return [n for n in names if n in ROADS]


def ask(messages):
    """First road that answers wins. Raises Unavailable only when every road fails."""
    errors = []
    for name in providers():
        try:
            return ROADS[name][0](messages)
        except Unavailable as e:
            errors.append(f"{name}: {e}")
            print(f"[CAI CHAT] {name} failed: {e}", flush=True)
    raise Unavailable(" | ".join(errors) or "no provider configured")


def live_road() -> str:
    return next((n for n in providers() if ROADS[n][1]()), "")


def up() -> bool:
    return bool(live_road())
