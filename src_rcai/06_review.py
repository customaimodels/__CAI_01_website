"""The scope reviewers behind Phase 2's "Ask to change the scope". Two passes, both MOCK today (no API key yet).

    check(scope, notes, tries)  -> the cheap first pass, on Save: which notes are too thin + one sharper ask.
                                   Pushes back twice at most; the third save goes through as written.
    review(scope, notes)        -> the second pass, on Review and send: ALWAYS returns 2-3 questions back
                                   to the client before anything reaches us.

notes = {"items": {"<index>": "comment", ...}, "add": "new capability text"}

config.yml  ai_cheap / ai_review  name the model; "mock" = these rules. A real model plugs in at _model()
once RCAI_AI_KEY is set (Railway variable; locally the environment). Until then nothing leaves the server.
"""
import os
import re

VAGUE = re.compile(r"\b(better|nicer|improve|more|less|stuff|things?|something|etc|fix|change it|update|cleaner|modern|good|bad)\b", re.I)
PUSH = [
    "Saved. A few notes are thin, so they're marked. Say what exactly, on which page or step, and for whom.",
    "Saved. One more pass on the marked notes: give an example. \"When X happens, Y should see Z\" works best.",
]


def mode(cfg):
    """mock until a key exists. The model names stay in config.yml so the swap is one line."""
    key = os.environ.get("RCAI_AI_KEY")
    return {"cheap": cfg.get("ai_cheap", "mock") if key else "mock",
            "review": cfg.get("ai_review", "mock") if key else "mock"}


def _words(t):
    return len(t.split())


def _vague(t):
    return _words(t) < 8 or (bool(VAGUE.search(t)) and not re.search(r"\d", t) and _words(t) < 16)


def _said(notes):
    items = {str(k): str(v).strip()[:800] for k, v in (notes.get("items") or {}).items() if str(v).strip()}
    return items, str(notes.get("add", "")).strip()[:1500]


def check(cfg, scope, notes, tries):
    items, add = _said(notes)
    if not items and not add:
        return {"ok": False, "say": "Write at least one comment or a new capability, then save."}
    weak = [k for k, t in items.items() if _vague(t)] + (["add"] if add and _vague(add) else [])
    if weak and tries < 2:
        return {"ok": False, "weak": weak, "say": PUSH[tries], "model": mode(cfg)["cheap"]}
    return {"ok": True, "weak": [], "model": mode(cfg)["cheap"],
            "say": "Saved. Read it once below, then send it to review."}


def review(cfg, scope, notes):
    """Always goes back with questions. Mock: picked from what is (not) in the notes, never generic filler."""
    items, add = _said(notes)
    names = scope.get("items") or []
    text = " ".join(list(items.values()) + [add]).lower()
    qs = []
    for k, t in list(items.items())[:2]:
        i = int(k) if k.isdigit() and int(k) < len(names) else None
        what = names[i] if i is not None else "this deliverable"
        qs.append(f"On \"{what}\": who notices the change first, and what do they see that they don't see today?")
    if add:
        qs.append("For the new capability: what is the first thing it should do, and how often does that happen?")
    if not re.search(r"\d", text):
        qs.append("Any numbers we should design for? Classes a week, people per class, how many admins.")
    if not re.search(r"\b(must|before|launch|go-live|date|week|deadline)\b", text):
        qs.append("Is any of this needed before go-live, or can it follow in a later pass?")
    return {"questions": qs[:3], "model": mode(cfg)["review"]}
