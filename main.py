"""Railway entry: the landing page (site/) and the chatbot API (chat/) on $PORT. Built by run.py --bundle."""
import os, runpy, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CAI_SITE", str(HERE / "site"))
sys.argv = ["run.py"]
os.chdir(HERE / "chat")
sys.path.insert(0, str(HERE / "chat"))
runpy.run_path(str(HERE / "chat" / "run.py"), run_name="__main__")
