"""Every path the chatbot touches. Nothing escapes ROOT."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DTA = ROOT / "dta"


def _in(p: Path) -> Path:
    p.resolve().relative_to(ROOT)  # raises if it escapes
    return p


CONFIG = _in(ROOT / "config.yml")
PROMPTS = _in(SRC / "00_prompts.yaml")
CORPUS = _in(DTA / "_0_raw" / "corpus")          # the knowledge: hand-written .md, one topic each
INDEX = _in(DTA / "_1_processed" / "index.json")  # built from CORPUS, never hand-edited
LEADS = _in(DTA / "_2_exports" / "leads.csv")     # the one thing the bot produces
