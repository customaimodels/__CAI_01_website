"""CAI chatbot engine. Modules are numbered (the law), so they load by name:
    from src import m;  m("05_retrieve").get_relevant_chunks("...")
"""
from importlib import import_module


def m(name):
    return import_module(f"{__name__}.{name}")
