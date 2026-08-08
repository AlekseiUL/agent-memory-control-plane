from __future__ import annotations
import json
from importlib.resources import files

def load_policy(name: str = "default") -> dict:
    path = files("amcp").joinpath("resources", "policies", f"{name}.yaml")
    return json.loads(path.read_text(encoding="utf-8"))

def resource_text(kind: str, name: str) -> str:
    return files("amcp").joinpath("resources", kind, name).read_text(encoding="utf-8")
