"""TF-IDF over section chunks: stopwords, plural folding, half-weight synonyms,
mild length penalty, at most 2 chunks per source. Returns [{id, source, title, content, score}]."""
import json
import math
from functools import lru_cache
from importlib import import_module

P = import_module("src.01_paths")
C = import_module("src.02_config")
T = import_module("src.03_text")
X = import_module("src.04_index")

MAX_PER_SOURCE = 2


@lru_cache()
def _index(mtime):
    return json.loads(P.INDEX.read_text(encoding="utf-8"))


def load():
    if X.stale():
        X.write()
    return _index(P.INDEX.stat().st_mtime)


def _diversify(scored, k):
    picked, over, per = [], [], {}
    for s in scored:
        if per.get(s["source"], 0) < MAX_PER_SOURCE:
            picked.append(s)
            per[s["source"]] = per.get(s["source"], 0) + 1
        else:
            over.append(s)
        if len(picked) >= k:
            return picked
    return picked + over[: k - len(picked)]


def get_relevant_chunks(query, max_results=None):
    k = C.get("top_k", 4, int)
    if max_results:
        k = min(k, max_results)
    floor = C.get("min_score", 0.0, float)
    idx = load()
    chunks, tf_by = idx.get("chunks", []), idx.get("chunk_tf", {})
    q = T.tokenize_set(query)
    if not chunks or not q:
        return []
    weights = T.expand_query(q)
    df = {}
    for tf in tf_by.values():
        for t in tf:
            df[t] = df.get(t, 0) + 1
    n = len(chunks)
    idf = lambda t: math.log(1.0 + n / df[t]) if t in df else 0.0
    qw = sum(idf(t) for t in q) or sum(idf(t) * w for t, w in weights.items())
    if qw <= 0:
        return []
    scored = []
    for c in chunks:
        tf = tf_by.get(c["id"]) or {}
        raw = sum(w * idf(t) * (1.0 + math.log(tf[t])) for t, w in weights.items() if tf.get(t))
        if raw <= 0:
            continue
        score = (raw / qw) / (1.0 + math.log(1.0 + len(tf) / 100.0))
        if score >= floor:
            scored.append({"id": c["id"], "source": c["source"], "title": c.get("title", c["source"]),
                           "content": c["content"], "score": score})
    scored.sort(key=lambda d: d["score"], reverse=True)
    return _diversify(scored, k)
