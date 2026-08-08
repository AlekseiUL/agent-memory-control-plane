from __future__ import annotations
import argparse, sys
from pathlib import Path
from .core import ControlPlane, PolicyDenied, NotFound, emit

def parser():
    p=argparse.ArgumentParser(prog="amcp",description="Agent Memory Control Plane")
    p.add_argument("--db",default=".amcp/control-plane.db")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("init")
    c=sub.add_parser("classify"); c.add_argument("content"); c.add_argument("--class-name"); c.add_argument("--dry-run",action="store_true")
    for name in ("propose","ingest"):
        x=sub.add_parser(name); x.add_argument("key"); x.add_argument("content"); x.add_argument("--source",default="profile-memory"); x.add_argument("--owner",default="assistant"); x.add_argument("--scope",default="private"); x.add_argument("--confidence",type=float,default=.8); x.add_argument("--class-name"); x.add_argument("--actor",default="contributor"); x.add_argument("--apply",action="store_true"); x.add_argument("--dry-run",action="store_true")
    x=sub.add_parser("promote"); x.add_argument("candidate_id",type=int); x.add_argument("--reviewer",default="reviewer"); x.add_argument("--apply",action="store_true")
    x=sub.add_parser("search"); x.add_argument("query"); x.add_argument("--actor",default="public_reader"); x.add_argument("--limit",type=int,default=10)
    x=sub.add_parser("explain"); x.add_argument("record_id",type=int); x.add_argument("--actor",default="public_reader")
    sub.add_parser("conflicts"); sub.add_parser("audit"); sub.add_parser("doctor")
    return p

def main(argv=None):
    a=parser().parse_args(argv); cp=ControlPlane(Path(a.db))
    try:
        if a.command=="init": out=cp.init()
        elif a.command=="classify": out=cp.classify(a.content,a.class_name)
        elif a.command in ("propose","ingest"): out=cp.propose(a.key,a.content,a.source,a.owner,a.scope,a.confidence,a.class_name,a.actor,apply=a.apply and not a.dry_run)
        elif a.command=="promote": out=cp.promote(a.candidate_id,a.reviewer,a.apply)
        elif a.command=="search": out=cp.search(a.query,a.actor,a.limit)
        elif a.command=="explain": out=cp.explain(a.record_id,a.actor)
        elif a.command=="conflicts": out=cp.conflicts()
        elif a.command=="audit": out=cp.audit()
        else: out=cp.doctor()
        print(emit(out)); return 0
    except (PolicyDenied,NotFound,ValueError) as exc:
        print(emit({"status":"denied","error":str(exc)}),file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
