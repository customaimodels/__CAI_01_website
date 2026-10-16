"""Question ──▶ CONTEXT from the corpus ──▶ model ──▶ reply. Deterministic fallback if the model is down."""
from importlib import import_module

C = import_module("src.02_config")
R = import_module("src.05_retrieve")
L = import_module("src.06_llm")

LEAD_FORM = "Name: <your name>\nEmail: <your email>\nProject: <one-line description>"


def _context(chunks):
    if not chunks:
        return "CONTEXT:\n\n(No additional context was retrieved.)"
    parts = ["CONTEXT:"]
    for i, c in enumerate(chunks, 1):
        parts += ["", f"[Snippet {i}]", c["content"].strip()]
    return "\n".join(parts)


def _from_record(chunks):
    """No model on this host: answer with the best matching passage of the corpus, verbatim. Never invents."""
    lines = [ln for ln in chunks[0]["content"].strip().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if lines and lines[0].startswith("[") and "]" in lines[0]:
        lines[0] = "**" + lines[0][1:].replace("]", " ·", 1).strip() + "**"  # "[Doc] Section" → bold head
    return ("\n".join(lines[:12]).strip() +
            "\n\nWant this for your business? Reply in this format and I'll follow up by email:\n\n" + LEAD_FORM)


def _overview():
    """A broad question matched nothing: answer with the services overview, never a script."""
    try:
        cs = [c for c in R.load().get("chunks", []) if c.get("source", "").startswith("services_overview")]
    except Exception:
        return []
    return cs[:1]


def fallback(text, chunks=None):
    if chunks and chunks[0].get("score", 0) > 0:
        return _from_record(chunks)
    ov = _overview()
    if ov and not any(w in text.lower() for w in ("price", "pricing", "cost", "$", "quote", "budget")):
        return _from_record(ov)
    t = text.lower()
    if any(w in t for w in ("price", "pricing", "cost", "$", "quote", "budget")):
        return ("Every CAI project is quoted after a short scope call: the number depends on how much of "
                "your business the system has to understand and safely act on.\n\n"
                "1) A short scope call.\n2) A written plan, timeline and price.\n3) A 50% deposit starts the work.\n\n"
                "Want a quote? Reply in this format and I'll follow up by email:\n\n" + LEAD_FORM)
    if "what can you build" in t or "what do you build" in t:
        return ("The short version of what CAI builds:\n\n"
                "- AI systems that sit on your own data and inside the tools you already use.\n"
                "- Assistants that find answers in your documents, with the source shown.\n"
                "- Automations that remove the manual glue work between your systems.\n"
                "- Forecasting and detection models where reliability matters.\n\n"
                "To see if your project fits, reply with:\n\n" + LEAD_FORM)
    return ("I'm answering from a short script right now, not the full assistant.\n\n"
            "CAI designs and ships AI systems built on your data and inside your workflow. "
            "The fastest way to know if your project fits is a short scope call. Reply with:\n\n" + LEAD_FORM)


def answer(history, question):
    """history: [{role, content}] before this question. Returns (reply, chunks, live)."""
    chunks = R.get_relevant_chunks(question)
    msgs = [
        {"role": "system", "content": C.system_prompt()},
        {"role": "system", "content": (
            "Facts (past projects, clients, numbers, prices) come ONLY from the CONTEXT block below; "
            "never make up a client or a result. How CAI would approach the visitor's task is yours to "
            "explain confidently, in plain business steps.\n\n" + _context(chunks))},
        *[m for m in history if m.get("role") in ("user", "assistant")],
        # Small models obey the latest instruction best; re-pin grounding before the user turn
        # (not after: llama3.2 returns empty content when the conversation ends on a system message).
        {"role": "system", "content": (
            "Reminder: every project, client, number and percentage you name must appear verbatim in "
            "CONTEXT. For the visitor's own task, answer directly: can it be automated, and the 2-4 steps "
            "of how we'd build it. Then offer a short scope call.")},
        {"role": "user", "content": question},
    ]
    try:
        return L.ask(msgs), chunks, True
    except L.Unavailable as e:
        print(f"[CAI CHAT] fallback: {e}", flush=True)
        return fallback(question, chunks), chunks, False
