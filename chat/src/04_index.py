"""dta/_0_raw/corpus/*.md  ──▶  dta/_1_processed/index.json   (section chunks + term counts)"""
import json
from importlib import import_module

P = import_module("src.01_paths")
T = import_module("src.03_text")

INDEX_VERSION = 3


def corpus():
    """[(stem, filename, title, text)] for every corpus doc, sorted."""
    out = []
    for p in sorted(P.CORPUS.glob("*.md")):
        text = p.read_text(encoding="utf-8").strip()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        out.append((p.stem, p.name, title, text))
    return out


def _sections(stem, source, title, text):
    chunks, head, lines = [], "", []

    def commit():
        body = "\n".join(lines).strip()
        if body:
            prefix = f"[{title}]" + (f" {head}" if head else "")
            chunks.append({"id": f"{stem}::{len(chunks)}", "source": source, "title": title,
                           "heading": head, "content": f"{prefix}\n{body}"})

    for line in text.splitlines():
        if line.startswith("## "):
            commit()
            head, lines = line[3:].strip(), []
        else:
            lines.append(line)
    commit()
    # A thin preamble outranks real sections on title words and starves the model: drop it.
    if len(chunks) > 1 and not chunks[0]["heading"] and len(T.tokenize_counts(chunks[0]["content"])) < 30:
        chunks = chunks[1:]
    return chunks


def build() -> dict:
    chunks, tf_by = [], {}
    for doc in corpus():
        for c in _sections(*doc):
            chunks.append(c)
            tf = T.tokenize_counts(c["content"])
            for t, n in T.tokenize_counts(c["heading"]).items():  # headings count twice
                tf[t] = tf.get(t, 0) + n
            tf_by[c["id"]] = tf
    return {"version": INDEX_VERSION, "chunks": chunks, "chunk_tf": tf_by}


def write() -> int:
    idx = build()
    P.INDEX.parent.mkdir(parents=True, exist_ok=True)
    P.INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(idx["chunks"])


def stale() -> bool:
    if not P.INDEX.exists():
        return True
    t = P.INDEX.stat().st_mtime
    return any(p.stat().st_mtime > t for p in P.CORPUS.glob("*.md"))
