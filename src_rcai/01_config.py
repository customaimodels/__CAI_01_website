"""Paths + the flat config.yml (the site root's). Every other R-CAI module reads from here.

Hosted (Railway) the repo is public, so three things come from the environment, never from git:
RCAI_CODE_SHA256 (the code word's hash) · RCAI_SECRET (signs the cookie) · RCAI_HUB_JSON (a snapshot of
the Clients Hub records, built by run.py --rcai-snapshot). Locally they come from config.yml, dta/ and the hub.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # __ss1_CAI_website
WEB = ROOT / "src_rcai" / "10_web"
RAW, PROC, EXP = (ROOT / "dta" / t for t in ("_0_raw", "_1_processed", "_2_exports"))
CONFIG = ROOT / "config.yml"
SECRET = PROC / "rcai" / "session.secret"   # signs the sign-in cookie; made on first run, never committed
LOG = EXP / "rcai" / "access.log"           # who signed in, when, ok or not -- pointers, no content
MOUNT = "/r-cai"                            # where the portal lives on the site, local and hosted


def load():
    cfg = {}
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        cfg[k.strip()] = v.split(" #")[0].strip()
    cfg["owners"] = [e.strip().lower() for e in cfg.get("owners", "").split(",") if e.strip()]
    cfg["links"] = {k[5:]: v for k, v in cfg.items() if k.startswith("link.")}
    for k in ("session_hours", "max_fails", "lockout_minutes"):
        cfg[k] = int(cfg[k])
    cfg["code_sha256"] = os.environ.get("RCAI_CODE_SHA256") or cfg.get("code_sha256", "")
    cfg["hub_json"] = os.environ.get("RCAI_HUB_JSON")
    cfg["hub"] = None if cfg["hub_json"] else (ROOT / cfg["hub_data"]).resolve()
    return cfg


def set_code(word):
    import hashlib
    h = hashlib.sha256(word.encode()).hexdigest()
    text = re.sub(r"^code_sha256:.*$", f"code_sha256: {h}", CONFIG.read_text(encoding="utf-8"), flags=re.M)
    CONFIG.write_text(text, encoding="utf-8")
    return h
