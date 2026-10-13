import importlib
import pkgutil
from pathlib import Path

PROGRAMS, SOURCES, DEVICES = {}, {}, {}

def register(table, name):
    def deco(cls):
        table[name] = cls
        return cls
    return deco

def build(table, spec, **extra):
    """{"type": "replay", "file": "x.pkl"} -> SOURCES["replay"](file="x.pkl", **extra)"""
    spec = dict(spec)
    kind = spec.pop("type")
    if kind not in table:
        raise ValueError(f"unknown type {kind!r}, registered: {sorted(table)}")
    return table[kind](**{**spec, **extra})

def load_plugins():
    """Import every module in sources/, devices/, programs/ so their @register runs.
    Hardware libraries (rpi_ws281x, gpiozero, obd...) must be imported lazily inside
    the classes, so this works on a dev machine too."""
    root = Path(__file__).resolve().parent
    for package in ("sources", "devices", "programs"):
        for module in pkgutil.iter_modules([str(root / package)]):
            importlib.import_module(f"{__package__}.{package}.{module.name}")
