"""Dependency-free JSON-RPC stdio adapter for MCP-compatible hosts."""
from __future__ import annotations
import json, sys
from pathlib import Path
from .core import ControlPlane
TOOLS=("memory_search","memory_explain","memory_propose","memory_promote","memory_conflicts","memory_source_get","memory_health")

def call(cp,name,args):
    if name=="memory_search": return cp.search(args["query"],args.get("actor","public_reader"),args.get("limit",10))
    if name=="memory_explain": return cp.explain(args["record_id"],args.get("actor","public_reader"))
    if name=="memory_propose": return cp.propose(args["key"],args["content"],args.get("source_id","profile-memory"),args.get("owner","assistant"),args.get("scope","private"),args.get("confidence",.8),args.get("class_name"),args.get("actor","assistant"),args.get("apply",False))
    if name=="memory_promote": return cp.promote(args["candidate_id"],args.get("reviewer","reviewer"),args.get("apply",False))
    if name=="memory_conflicts": return cp.conflicts()
    if name=="memory_source_get": return cp.source_get(args["source_id"])
    if name=="memory_health": return cp.doctor()
    raise ValueError("unknown tool")

def dispatch(cp,req):
    method=req.get("method"); rid=req.get("id")
    if method=="initialize": result={"protocolVersion":"2024-11-05","serverInfo":{"name":"amcp","version":"0.1.0"},"capabilities":{"tools":{}}}
    elif method=="tools/list": result={"tools":[{"name":n,"description":n.replace("_"," "),"inputSchema":{"type":"object"}} for n in TOOLS]}
    elif method=="tools/call":
        params=req.get("params",{}); value=call(cp,params["name"],params.get("arguments",{})); result={"content":[{"type":"text","text":json.dumps(value,ensure_ascii=False)}]}
    else: return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"method not found"}}
    return {"jsonrpc":"2.0","id":rid,"result":result}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--db",default=".amcp/control-plane.db"); p.add_argument("--list-tools",action="store_true"); a=p.parse_args(argv)
    cp=ControlPlane(Path(a.db))
    if a.list_tools: print(json.dumps({"tools":TOOLS})); return 0
    for line in sys.stdin:
        try: response=dispatch(cp,json.loads(line))
        except Exception as exc: response={"jsonrpc":"2.0","id":None,"error":{"code":-32000,"message":str(exc)}}
        print(json.dumps(response)); sys.stdout.flush()
    return 0
if __name__=="__main__": raise SystemExit(main())
