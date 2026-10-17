"""MEDIUM (2026-10-17): one article → <slug>/medium.md, git-tracked markdown with SEO frontmatter.
Medium's API is closed, so nothing here posts. The markdown is the record (title · date · tags · canonical_url);
Medium's Import Story reads the LIVE page URL and sets canonical to it, so customaimodels.com keeps the SEO credit.
Stdlib only. Run: python3 run.py --medium <slug|all>. Never served (.md is not in articles.TYPES)."""
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://customaimodels.com"


class _MD(HTMLParser):
    """The <article class="art-body"> block only, as plain markdown. Inline: strong/em/code/a. Block: p/h2/h3/ul/ol/li/figure."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.out, self.buf, self.on, self.href, self.lists = base, [], "", False, None, []

    def _flush(self, prefix=""):
        t = re.sub(r"\s+", " ", self.buf).strip()
        if t:
            self.out.append(prefix + t)
        self.buf = ""

    def handle_starttag(self, tag, at):
        at = dict(at)
        if tag == "article" and "art-body" in (at.get("class") or ""):
            self.on = True
        if not self.on:
            return
        if tag in ("strong", "b"):
            self.buf += "**"
        elif tag in ("em", "i"):
            self.buf += "*"
        elif tag == "code":
            self.buf += "`"
        elif tag == "a":
            self.href = at.get("href", "")
            self.buf += "["
        elif tag in ("ul", "ol"):
            self.lists.append(tag)
        elif tag == "img":
            src = at.get("src", "")
            src = src if src.startswith("http") else f"{SITE}/articles/{(self.base / src).as_posix()}"
            src = re.sub(r"/[^/]+/\.\./", "/", src)
            self.out.append(f"![{at.get('alt', '')}]({src})")

    def handle_endtag(self, tag):
        if not self.on:
            return
        if tag == "article":
            self._flush()
            self.on = False
        elif tag in ("strong", "b"):
            self.buf += "**"
        elif tag in ("em", "i"):
            self.buf += "*"
        elif tag == "code":
            self.buf += "`"
        elif tag == "a":
            h = self.href or ""
            h = h if h.startswith(("http", "mailto:")) else SITE + ("" if h.startswith("/") else "/articles/") + h.lstrip("./")
            self.buf += f"]({h})"
        elif tag == "p":
            self._flush()
        elif tag in ("h2", "h3"):
            self._flush("## " if tag == "h2" else "### ")
        elif tag == "figcaption":
            t = re.sub(r"\s+", " ", self.buf).strip()
            self.buf = ""
            if t:
                self.out.append(f"*{t}*")
        elif tag == "li":
            self._flush("- " if self.lists and self.lists[-1] == "ul" else "1. ")
        elif tag in ("ul", "ol") and self.lists:
            self.lists.pop()

    def handle_data(self, d):
        if self.on:
            self.buf += d


def export(slug):
    d = HERE / slug
    meta = json.loads((d / "meta.json").read_text())
    p = _MD(Path(slug))
    p.feed((d / "index.html").read_text())
    url = meta.get("url") or f"{SITE}/articles/{slug}/"
    tags = ", ".join(f'"{t}"' for t in meta.get("tags", [])[:5])   # Medium keeps 5 tags at most
    front = (f'---\ntitle: "{meta["title"]}"\nsubtitle: "{meta.get("deck", "")}"\ndate: {meta["date"]}\n'
             f'author: "{meta.get("author", "Yeriko Vargas")}"\ntags: [{tags}]\ncanonical_url: "{url}"\n---\n')
    body = "\n\n".join(unescape(x) for x in p.out)
    tail = f"\n\n---\n\n*Originally published at [customaimodels.com]({url}).*\n"
    f = d / "medium.md"
    f.write_text(f"{front}\n# {meta['title']}\n\n{body}{tail}")
    return f, url


def run(which):
    slugs = sorted(x.name for x in HERE.iterdir() if (x / "meta.json").is_file()) if which == "all" else [which]
    for s in slugs:
        f, url = export(s)
        print(f"✓ {f.relative_to(HERE.parent)}\n  import from {url}")
    return 0
