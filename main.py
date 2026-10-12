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
GET, POST = door.Door.do_GET, door.Door.do_POST
door.Door.do_GET = lambda h: portal.handle(h, "GET") or GET(h)
door.Door.do_POST = lambda h: portal.handle(h, "POST") or POST(h)
door.serve()
