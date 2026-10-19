"""src_follow_up · the sign-up FOLLOW-UP. The "we have your request" email becomes a door into their problem.

    rank(need)                 -> the doors, closest first (a default RAG: stdlib word overlap of what they
                                  wrote against each door's words + the title/body of the article it opens)
    link(email, door_id, base) -> a signed /r-cai/api/door?... URL (the click is logged, then 302 to the page)
    open_(query)               -> (href, row) for a valid click, else (None, None)

Doors live in doors.json (his file, max 10). No model call, no network, no fake claims: every door opens a
live public page. PROPOSAL until he says yes: a real retrieval index over the articles (embeddings) and
PATH B (the article-click sign-up, its own door set).
"""
import hashlib
import hmac
import json
import re
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTICLES = HERE.parent / "src_articles"
_W = re.compile(r"[a-z][a-z\-]{2,}")
STOP = set("the and for with that this our are was were have has had from you your not but can will just them they into than then what when who how why all any one out get got its".split())


def _words(text):
    return [w for w in _W.findall((text or "").lower()) if w not in STOP]


def doors():
    return json.loads((HERE / "doors.json").read_text(encoding="utf-8"))


def _article(href):
    """title + first ~400 words of the article a door opens (its medium.md, the same copy Medium imports)."""
    slug = href.strip("/").split("/")[-1] if href.startswith("/articles/") else ""
    md = ARTICLES / slug / "medium.md" if slug else None
    if not md or not md.exists():
        return ""
    return " ".join(md.read_text(encoding="utf-8").split()[:400])


def rank(need):
    d = doors()["doors"]
    q = set(_words(need))
    out = []
    for i, door in enumerate(d):
        if not door.get("words"):                       # the catch-all door always sits last
            out.append((-1.0, i, door))
            continue
        own = set(_words(door["words"] + " " + door["title"]))
        body = set(_words(_article(door["href"])))
        score = 3 * len(q & own) + len(q & body) / 4
        out.append((score, i, door))
    out.sort(key=lambda t: (-t[0], t[1]))
    return [dict(door, score=round(s, 2)) for s, _, door in out]


def _secret():
    return __import__("importlib").import_module("src_rcai.03_auth")._secret()


def _sig(email, door_id):
    return hmac.new(_secret(), f"door|{email}|{door_id}".encode(), hashlib.sha256).hexdigest()[:24]


def link(email, door_id, base):
    q = urllib.parse.urlencode({"d": door_id, "e": email, "s": _sig(email, door_id)})
    return f"{base.rstrip('/')}/r-cai/api/door?{q}"


def open_(query):
    p = urllib.parse.parse_qs(query or "")
    d, e, s = (p.get(k, [""])[0] for k in ("d", "e", "s"))
    door = next((x for x in doors()["doors"] if x["id"] == d), None)
    if not door or not e or not hmac.compare_digest(s, _sig(e, d)):
        return None, None
    href = door["href"] + ("&" if "?" in door["href"] else "?") + doors()["utm"] + f"&utm_content={d}"
    return href, {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "email": e.lower(), "door": d, "title": door["title"]}
