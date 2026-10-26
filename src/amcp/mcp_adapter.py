"""Bounded JSON-RPC stdio adapter. Identity is supplied by the trusted launcher."""
from __future__ import annotations
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from .core import ControlPlane, PolicyDenied, NotFound


@dataclass(frozen=True)
class Identity:
    actor: str = "public_reader"
    can_propose: bool = False
    can_promote: bool = False


DEFAULT_IDENTITY = Identity()
STRING = {"type": "string", "minLength": 1}
ID = {"type": "integer", "minimum": 1}
BOOL = {"type": "boolean", "default": False}


def schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


SCHEMAS = {
    "memory_search": schema({"query": STRING, "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 10}}, ("query",)),
    "memory_explain": schema({"record_id": ID}, ("record_id",)),
    "memory_propose": schema({"key": STRING, "content": STRING, "source_id": STRING, "owner": STRING,
                              "scope": {"type": "string", "enum": ["private", "team", "public"]},
                              "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                              "class_name": {"type": "string", "enum": ["stable_fact", "procedure", "team_policy", "non_memory"]},
                              "apply": BOOL}, ("key", "content")),
    "memory_promote": schema({"candidate_id": ID, "apply": BOOL}, ("candidate_id",)),
    "memory_conflicts": schema({}),
    "memory_source_get": schema({"source_id": STRING}, ("source_id",)),
    "memory_health": schema({}),
}
TOOLS = tuple(SCHEMAS)


def available_tools(cp, identity):
    names = ["memory_search", "memory_explain", "memory_source_get", "memory_health"]
    if identity.can_propose and "candidate" in cp.policy["capabilities"].get(identity.actor, {}).get("write_modes", []):
        names.append("memory_propose")
    if identity.can_promote and identity.actor in cp.policy["promotion"]["reviewer_roles"]:
        names.append("memory_promote")
    # Conflict entries expose IDs of private candidates; only the all-scope role may inspect them.
    if set(cp.policy["scopes"]) <= set(cp.policy["access"].get(identity.actor, [])):
        names.append("memory_conflicts")
    return names


def validate(name, args):
    spec = SCHEMAS[name]
    if not isinstance(args, dict) or set(args) - set(spec["properties"]) or set(spec["required"]) - set(args):
        raise ValueError("invalid tool arguments")
    types = {"string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,)}
    for key, value in args.items():
        rule = spec["properties"][key]
        if type(value) not in types[rule["type"]]:
            raise ValueError(f"invalid type: {key}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value) or value < rule.get("minimum", -math.inf) or value > rule.get("maximum", math.inf):
                raise ValueError(f"out of range: {key}")
        if "minLength" in rule and isinstance(value, str) and len(value) < rule["minLength"]:
            raise ValueError(f"empty field: {key}")
        if "enum" in rule and value not in rule["enum"]:
            raise ValueError(f"invalid value: {key}")


def call(cp, name, args, identity=DEFAULT_IDENTITY):
    if name not in available_tools(cp, identity):
        raise PolicyDenied("tool unavailable for this identity")
    validate(name, args)
    actor = identity.actor
    if name == "memory_search": return cp.search(args["query"], actor, args.get("limit", 10))
    if name == "memory_explain": return cp.explain(args["record_id"], actor)
    if name == "memory_propose":
        return cp.propose(args["key"], args["content"], args.get("source_id", "profile-memory"), args.get("owner", "assistant"), args.get("scope", "private"), args.get("confidence", .8), args.get("class_name"), actor, args.get("apply", False))
    if name == "memory_promote": return cp.promote(args["candidate_id"], actor, args.get("apply", False))
    if name == "memory_conflicts": return cp.conflicts()
    if name == "memory_source_get":
        result = cp.source_get(args["source_id"])
        if not cp._scope_allowed(actor, result["scope"]): raise PolicyDenied("scope denied")
        return result
    if name == "memory_health": return cp.doctor()
    raise ValueError("unknown tool")


def error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def dispatch(cp, req, identity=DEFAULT_IDENTITY):
    if not isinstance(req, dict): return error(None, -32600, "invalid request")
    rid = req.get("id")
    if req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str) or (rid is not None and type(rid) not in (str, int)):
        return error(None, -32600, "invalid request")
    # No tool execution on notifications, including malformed tools/call notifications.
    if "id" not in req: return None
    method = req["method"]
    try:
        if method == "initialize": result = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "amcp", "version": "0.1.0"}, "capabilities": {"tools": {}}}
        elif method == "ping": result = {}
        elif method == "tools/list": result = {"tools": [{"name": n, "description": n.replace("_", " "), "inputSchema": SCHEMAS[n]} for n in available_tools(cp, identity)]}
        elif method == "tools/call":
            params = req.get("params", {})
            if not isinstance(params, dict) or not isinstance(params.get("name"), str): raise ValueError("invalid params")
            value = call(cp, params["name"], params.get("arguments", {}), identity)
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
        else: return error(rid, -32601, "method not found")
    except (ValueError, KeyError, TypeError): return error(rid, -32602, "invalid params")
    except (PolicyDenied, NotFound): return error(rid, -32000, "operation denied or unavailable")
    except Exception: return error(rid, -32603, "internal error")
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=".amcp/control-plane.db")
    p.add_argument("--list-tools", action="store_true")
    p.add_argument("--identity", default="public_reader", help="Trusted launcher role, never tool payload")
    p.add_argument("--allow-propose", action="store_true")
    p.add_argument("--allow-promote", action="store_true", help="Separate reviewer-only launcher; never grant to the proposing agent")
    a = p.parse_args(argv)
    cp = ControlPlane(Path(a.db))
    identity = Identity(a.identity, a.allow_propose, a.allow_promote)
    if a.list_tools:
        print(json.dumps({"tools": available_tools(cp, identity)}))
        return 0
    for line in sys.stdin:
        try: req = json.loads(line)
        except ValueError: response = error(None, -32700, "parse error")
        else: response = dispatch(cp, req, identity)
        if response is not None:
            print(json.dumps(response))
            sys.stdout.flush()
    return 0


if __name__ == "__main__": raise SystemExit(main())
