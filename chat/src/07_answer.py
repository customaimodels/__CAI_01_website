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


def fallback(text, chunks=None):
    if chunks and chunks[0].get("score", 0) > 0:
        return _from_record(chunks)
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
            "You must answer ONLY using the information in the CONTEXT block below. The ONLY projects, "
            "clients and examples you may mention are the ones described there; never make up new ones, "
            "even as illustrations. If the answer is not covered, say you don't know and suggest a short "
            "scope call instead.\n\n" + _context(chunks))},
        *[m for m in history if m.get("role") in ("user", "assistant")],
        # Small models obey the latest instruction best; re-pin grounding before the user turn
        # (not after: llama3.2 returns empty content when the conversation ends on a system message).
        {"role": "system", "content": (
            "Reminder: every project, client, number and percentage in your reply must appear verbatim "
            "in the CONTEXT block above. If CONTEXT has no concrete example for what was asked, say so "
            "plainly and suggest a short scope call; do not invent one.")},
        {"role": "user", "content": question},
    ]
    try:
        return L.ask(msgs), chunks, True
    except L.Unavailable as e:
        print(f"[CAI CHAT] fallback: {e}", flush=True)
        return fallback(question, chunks), chunks, False
