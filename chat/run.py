"""CAI CHATBOT · __ss2_ChatBot · stdlib python3 -- the front door.

python3 run.py              serve the chat API on 127.0.0.1:8190 (the landing page talks to it)
python3 run.py --ask "..."  one question in the terminal, with its sources
python3 run.py --index      rebuild dta/_1_processed/index.json from dta/_0_raw/corpus/
python3 run.py --check      compile + golden retrieval + lead parser + fallback; exit 1 on any ✗

Stdlib only, no .venv to enter. Model roads: config.yml provider (claude login, API, Ollama). Local preview, never a deploy.
"""
import argparse
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src import m  # noqa: E402

TITLE = f"CAI CHATBOT · {ROOT.name} · py{sys.version_info.major}.{sys.version_info.minor} (stdlib)"


def check():
    bad = 0

    def say(ok, msg):
        nonlocal bad
        bad += not ok
        print(("✓ " if ok else "✗ ") + msg)

    for f in sorted([ROOT / "run.py", *(ROOT / "src").glob("*.py")]):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            say(False, f"compile {f.name}: {e.msg}")
    say(True, "compile")
    say(m("04_index").write() > 0, "index built from corpus")
    R = m("05_retrieve")
    gold = m("11_golden").GOLDEN
    hit = sum((R.get_relevant_chunks(q) or [{}])[0].get("source") == want for q, want in gold)
    say(hit == len(gold), f"golden retrieval {hit}/{len(gold)}")
    D = m("08_leads")
    say(D.parse("Name: A B\nEmail: a@b.co\nProject: x") is not None, "lead parser takes the 3 lines")
    say(D.parse("Name: A\nEmail: nope\nProject: x") is None, "lead parser refuses a bad email")
    say("Name:" in m("07_answer").fallback("what does it cost"), "fallback asks for the 3 lines")
    say(bool(m("02_config").system_prompt()), "prompts load")
    print("✓ clean" if not bad else f"✗ {bad} failed")
    return 1 if bad else 0


def ask(q):
    out = m("09_chat").turn(None, q)
    print(out["reply"], "\n")
    print("· sources:", ", ".join(out["sources"]) or "none", "· live" if out["live"] else "· FALLBACK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=TITLE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--ask")
    ap.add_argument("--port", type=int)
    a = ap.parse_args()
    print((f"\033]0;{TITLE}\007" if sys.stdout.isatty() else "") + TITLE, flush=True)
    if a.check:
        sys.exit(check())
    if a.index:
        print(f"✓ {m('04_index').write()} chunks → dta/_1_processed/index.json")
        sys.exit(0)
    if a.ask:
        sys.exit(ask(a.ask))
    m("10_server").serve(a.port)
