"""Railway entry: landing (site/), R-CAI (src_rcai/, at /r-cai) and the chatbot API (chat/) on $PORT.
Built by __ss1_CAI_website/run.py --bundle. R-CAI's data, code hash and cookie secret come from Railway
variables (RCAI_HUB_JSON, RCAI_CODE_SHA256, RCAI_SECRET) -- this repo is public, they are never in it."""
import os, sys
from importlib import import_module
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CAI_SITE", str(HERE / "site"))
sys.path[:0] = [str(HERE / "chat"), str(HERE)]
os.chdir(HERE / "chat")
door = import_module("src.10_server")
portal = import_module("src_rcai.04_server")
vault = import_module("src_y_vault.vault")
rec = import_module("src_recruiter.recruiter")
read = import_module("src_articles.articles")
mind = import_module("src_brain.brain")
hits = import_module("src_util_stats.stats")
GET, POST = door.Door.do_GET, door.Door.do_POST
door.Door.do_GET = lambda h: hits.handle(h, "GET") or portal.handle(h, "GET") or vault.handle(h, "GET") or rec.handle(h, "GET") or mind.handle(h, "GET") or read.handle(h, "GET") or GET(h)
door.Door.do_POST = lambda h: hits.handle(h, "POST") or portal.handle(h, "POST") or vault.handle(h, "POST") or rec.handle(h, "POST") or mind.handle(h, "POST") or POST(h)
def _head(h):  # HEAD = GET's status + headers, body dropped (crawlers probe with HEAD; it was a 501)
    import io
    end = h.end_headers
    def _end():
        end()
        h.wfile = io.BytesIO()
    h.end_headers = _end
    h.do_GET()
door.Door.do_HEAD = _head
door.serve()
