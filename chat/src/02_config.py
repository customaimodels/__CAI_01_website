"""config.yml (flat key: value) and src/00_prompts.yaml (block scalars). No PyYAML needed."""
from functools import lru_cache
from importlib import import_module

P = import_module("src.01_paths")


@lru_cache()
def config() -> dict:
    out = {}
    for raw in P.CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def get(key, default=None, cast=str):
    v = config().get(key, "")
    return cast(v) if v != "" else default


@lru_cache()
def prompts() -> dict:
    out, key, buf = {}, None, []
    for raw in P.PROMPTS.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            if key and raw.strip() == "":
                buf.append("")
            continue
        if not raw.startswith(" ") and ":" in raw:
            if key:
                out[key] = "\n".join(buf).strip()
            key, rest = raw.split(":", 1)
            key, buf = key.strip(), []
            if rest.strip() != "|":
                out[key], key = rest.strip(), None
            continue
        if key:
            buf.append(raw[2:] if raw.startswith("  ") else raw)
    if key:
        out[key] = "\n".join(buf).strip()
    return out


def system_prompt() -> str:
    p = prompts()
    return "\n\n".join(x for x in (p.get("system_public", ""), p.get("safety", "")) if x.strip())
