#!/usr/bin/env python3
from __future__ import annotations
import json, tempfile
from pathlib import Path
from amcp.core import ControlPlane

def promote(cp,key,content,source,owner,scope,actor):
    candidate=cp.propose(key,content,source,owner,scope,.9,actor=actor,apply=True)
    return cp.promote(candidate["candidate_id"],apply=True)

def run():
    with tempfile.TemporaryDirectory(prefix="amcp-demo-") as tmp:
        cp=ControlPlane(Path(tmp)/"demo.db"); cp.init(); traces=[]
        personal=promote(cp,"response-style","The preferred format is concise","profile-memory","assistant","private","assistant")
        traces.append({"scenario":"personal_assistant","promotion":personal,"retrieval":cp.search("concise",actor="assistant")})
        team=promote(cp,"release-rule","Team policy must require reviewer approval","governance","dispatcher","team","dispatcher")
        traces.append({"scenario":"multi_agent_team","roles":["dispatcher","researcher","writer","developer","reviewer"],"promotion":team,"retrieval":cp.search("reviewer",actor="team_member")})
        public=promote(cp,"public-guide","Public onboarding guide","public-knowledge","researcher","public","researcher")
        private=promote(cp,"private-note","Private workspace preference","profile-memory","assistant","private","assistant")
        traces.append({"scenario":"public_private_boundary","public_result":cp.search("guide",actor="public_reader"),"private_result":cp.search("preference",actor="public_reader"),"private_record_id":private["record_id"],"public_record_id":public["record_id"]})
        print(json.dumps({"status":"ok","scenarios":traces},ensure_ascii=False,indent=2))
        return traces
if __name__=="__main__": run()
