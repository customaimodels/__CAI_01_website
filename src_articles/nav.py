"""The article bar, built from nav.yml (the spotlight) onto every page in src_articles.

    python3 src_articles/nav.py          rewrites <nav aria-label="Articles"> on every page
    python3 src_articles/nav.py --check  exits 1 if a page differs from nav.yml, or nav.yml is wrong

The bar is steady: the same spotlight on every page, "Articles" first. The open page is marked
(aria-current) only when it is in the spotlight. Stdlib only (the site .venv has no PyYAML).
"""
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAV = re.compile(r'(<nav aria-label="Articles">)(.*?)(\n  </nav>)', re.S)


def load():
    """nav.yml -> (max, [{slug, label}]). A strict small shape: max + spotlight rows."""
    mx, rows = 6, []
    for raw in (HERE / "nav.yml").read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"max:\s*(\d+)$", line)
        if m:
            mx = int(m.group(1))
            continue
        m = re.match(r"\s*-\s*slug:\s*(\S+)$", line)
        if m:
            rows.append({"slug": m.group(1), "label": ""})
            continue
        m = re.match(r"\s+label:\s*(.+)$", line)
        if m and rows:
            rows[-1]["label"] = m.group(1).strip().strip('"')
    return mx, rows


def problems():
    mx, rows = load()
    out = []
    if len(rows) > mx:
        out.append(f"nav.yml: {len(rows)} rows, max is {mx}")
    seen = set()
    for r in rows:
        if not (HERE / r["slug"] / "meta.json").is_file():
            out.append(f"nav.yml: {r['slug']} is not an article folder")
        if not r["label"]:
            out.append(f"nav.yml: {r['slug']} has no label")
        if r["slug"] in seen:
            out.append(f"nav.yml: {r['slug']} twice")
        seen.add(r["slug"])
    return out


def block(current):
    """The inside of the <nav> for a page whose slug is `current` ("" = the /articles/ index)."""
    _, rows = load()
    cur = ' aria-current="page"' if current == "" else ""
    out = [f'\n   <a href="/articles/"{cur}>Articles</a>']
    for r in rows:
        cur = ' aria-current="page"' if r["slug"] == current else ""
        out.append(f'   <a href="/articles/{r["slug"]}/"{cur}>{escape(r["label"])}</a>')
    return "\n".join(out)


def pages():
    out = [("", HERE / "index.html")]
    for d in sorted(p for p in HERE.iterdir() if p.is_dir() and (p / "index.html").exists()):
        out.append((d.name, d / "index.html"))
    return out


def apply(check=False):
    drift = problems()
    if drift:
        return drift
    for slug, f in pages():
        s = f.read_text(encoding="utf-8")
        m = NAV.search(s)
        if not m:
            drift.append(f"{f.relative_to(HERE)}: no article nav")
            continue
        want = block(slug)
        if m.group(2) != want:
            if check:
                drift.append(f"{f.relative_to(HERE)}: nav differs from nav.yml")
            else:
                f.write_text(s[:m.start(2)] + want + s[m.end(2):], encoding="utf-8")
    return drift


if __name__ == "__main__":
    chk = "--check" in sys.argv
    d = apply(check=chk)
    for x in d:
        print("  ✗", x)
    print(f"nav: {len(pages())} pages · {len(load()[1])} in the spotlight · {'drift ' + str(len(d)) if d else 'ok'}")
    sys.exit(1 if d else 0)
