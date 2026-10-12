"""
Shared text processing: tokenization, normalization, stopwords, synonyms.
stopwords, and the business-term synonym map. Used by both build_index
(index time) and retrieve (query time) so the two always agree.
"""
import re
from typing import Dict, List, Set

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")

# Function words and query fillers. With a small corpus, IDF alone can't
# neutralize these ("show me ..." matching a doc that quotes "Show me ...").
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "could",
    "do", "does", "for", "from", "get", "give", "have", "how", "i", "in",
    "is", "it", "its", "me", "my", "of", "on", "or", "our", "please",
    "show", "tell", "that", "the", "their", "them", "they", "this", "to",
    "us", "we", "what", "when", "where", "which", "who", "why", "will",
    "with", "would", "you", "your",
}

# Query expansion: business vocabulary visitors use -> corpus vocabulary.
# Keys and values are normalized tokens (see normalize_token). Expanded
# terms score at half weight so literal matches always win ties.
SYNONYMS: Dict[str, List[str]] = {
    "cost": ["price", "pricing", "fee", "quote", "budget"],
    "price": ["cost", "pricing", "fee", "quote"],
    "pricing": ["cost", "price", "fee", "quote"],
    "charge": ["cost", "price", "fee", "quote"],
    "fee": ["cost", "price", "pricing"],
    "pay": ["deposit", "price", "fee", "paypal"],
    "payment": ["deposit", "price", "fee", "paypal"],
    "build": ["design", "ship", "implement", "system"],
    "create": ["build", "design", "ship"],
    "make": ["build", "design", "ship"],
    "develop": ["build", "design", "ship"],
    "proof": ["project", "outcome", "deployment", "example"],
    "portfolio": ["project", "proof", "outcome"],
    "experience": ["project", "proof", "outcome"],
    "start": ["scope", "call", "deposit", "kickoff"],
    "started": ["scope", "call", "deposit", "kickoff"],
    "begin": ["scope", "call", "deposit", "kickoff"],
    "hire": ["scope", "call", "engagement"],
    "chatbot": ["assistant", "agent", "rag"],
    "bot": ["assistant", "agent", "rag"],
    "llm": ["model", "rag", "agent"],
    "gpt": ["model", "llm", "rag"],
    "diligence": ["deal", "memo", "document", "retrieval"],
    "vdr": ["deal", "document", "data", "room"],
    "ic": ["committee", "investment", "memo", "decision"],
    "memo": ["deal", "document", "decision"],
    "private": ["local", "confidential", "anonymized"],
    "secure": ["local", "confidential", "private"],
    "audio": ["venue", "sound", "operation"],
    "forecast": ["timeserie", "model", "pipeline"],
    "fraud": ["anomaly", "detection", "scoring"],
}


# Irregular verb forms the plural-s stemmer can't connect ("What CAI built"
# must match queries asking what CAI can "build").
_IRREGULAR = {
    "built": "build",
    "shipped": "ship",
    "designed": "design",
    "deployed": "deploy",
    "ran": "run",
}


def normalize_token(token: str) -> str:
    """Light plural-s stemming plus a few irregular verb forms."""
    token = _IRREGULAR.get(token, token)
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize_counts(text: str) -> Dict[str, int]:
    """Normalized term frequencies, stopwords removed."""
    counts: Dict[str, int] = {}
    for m in _WORD_RE.finditer(text):
        t = m.group(0).lower()
        if t in STOPWORDS:
            continue
        t = normalize_token(t)
        counts[t] = counts.get(t, 0) + 1
    return counts


def tokenize_set(text: str) -> Set[str]:
    return set(tokenize_counts(text).keys())


def expand_query(q_tokens: Set[str]) -> Dict[str, float]:
    """
    Map query tokens to weights: literal tokens at 1.0, synonym expansions
    at 0.5 (never overriding a literal).
    """
    weights: Dict[str, float] = {t: 1.0 for t in q_tokens}
    for t in q_tokens:
        for syn in SYNONYMS.get(t, []):
            syn = normalize_token(syn)
            if syn not in weights:
                weights[syn] = 0.5
    return weights
