import json, tempfile, unittest
from pathlib import Path
from amcp.core import ControlPlane, PolicyDenied
from amcp.mcp_adapter import TOOLS, dispatch

class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"test.db"; self.cp=ControlPlane(self.db); self.cp.init()
    def tearDown(self): self.tmp.cleanup()
    def proposed(self,key="fact",content="The preferred format is concise",source="public-knowledge",scope="public",apply=True):
        return self.cp.propose(key,content,source,"researcher",scope,.9,apply=apply)
    def promoted(self,**kwargs):
        candidate=self.proposed(**kwargs); return self.cp.promote(candidate["candidate_id"],apply=True)
    def test_init_fail_closed(self):
        result=self.cp.doctor(); self.assertEqual(result["status"],"ok"); self.assertTrue(result["checks"]["local_only"]); self.assertTrue(result["checks"]["llm_write_disabled"])
    def test_classification_routing(self):
        self.assertEqual(self.cp.classify("A procedure with step one")["writeback_target"],"procedures")
        self.assertEqual(self.cp.classify("team policy must be reviewed")["writeback_target"],"governance/policy.md")
    def test_non_memory_rejected(self): self.assertFalse(self.cp.classify("temporary task status")["allowed"])
    def test_secret_pattern_rejected(self):
        value="api"+"_key"+"="+"syntheticvalue123"; self.assertFalse(self.cp.classify(value)["allowed"])
    def test_dry_run_has_no_mutation(self):
        self.proposed(apply=False); self.assertEqual(self.cp.audit()["counts"]["candidates"],0)
    def test_promotion_dry_run(self):
        candidate=self.proposed(); receipt=self.cp.promote(candidate["candidate_id"]); self.assertTrue(receipt["dry_run"]); self.assertEqual(self.cp.audit()["counts"]["records"],0)
    def test_provenance_receipt(self):
        record=self.promoted(); receipt=self.cp.explain(record["record_id"])
        for field in ("source","owner","scope","confidence","updated_at","retrieval_reason","writeback_target","conflict_signal","staleness_signal"): self.assertIn(field,receipt)
    def test_scope_denial_filters_search(self):
        self.promoted(source="profile-memory",scope="private"); self.assertEqual(self.cp.search("preferred",actor="public_reader"),[])
    def test_scope_denial_explain(self):
        record=self.promoted(source="profile-memory",scope="private")
        with self.assertRaises(PolicyDenied): self.cp.explain(record["record_id"],actor="public_reader")
    def test_precedence_blocks_lower_priority(self):
        high=self.proposed(key="rule",content="Canonical value",source="governance",scope="team"); self.cp.promote(high["candidate_id"],apply=True)
        low=self.proposed(key="rule",content="Memory override",source="profile-memory",scope="private"); receipt=self.cp.promote(low["candidate_id"],apply=True)
        self.assertEqual(receipt["decision"],"conflict"); self.assertEqual(len(self.cp.conflicts()),1)
    def test_supersession(self):
        first=self.promoted(key="topic",content="Version one")
        second_candidate=self.proposed(key="topic",content="Version two"); second=self.cp.promote(second_candidate["candidate_id"],apply=True)
        self.assertEqual(second["supersedes"],first["record_id"]); self.assertEqual(len(self.cp.search("Version")),1)
    def test_conflict_signal_in_explain(self):
        high=self.proposed(key="rule",content="Canonical value",source="governance",scope="team"); rec=self.cp.promote(high["candidate_id"],apply=True)
        low=self.proposed(key="rule",content="Override",source="profile-memory",scope="private"); self.cp.promote(low["candidate_id"],apply=True)
        self.assertTrue(self.cp.explain(rec["record_id"],actor="team_member")["conflict_signal"])
    def test_unknown_scope_denied(self):
        with self.assertRaises(PolicyDenied): self.cp.propose("k","value","profile-memory","assistant","unknown",apply=True)
    def test_audit_provenance(self):
        candidate=self.proposed(); self.cp.promote(candidate["candidate_id"],apply=True); self.assertEqual(self.cp.audit()["counts"]["audit_log"],2)
    def test_mcp_tool_surface(self):
        expected={"memory_search","memory_explain","memory_propose","memory_promote","memory_conflicts","memory_source_get","memory_health"}; self.assertEqual(set(TOOLS),expected)
        response=dispatch(self.cp,{"jsonrpc":"2.0","id":1,"method":"tools/list"}); self.assertEqual({x["name"] for x in response["result"]["tools"]},expected)
    def test_source_get(self): self.assertEqual(self.cp.source_get("governance")["priority"],100)

if __name__=="__main__": unittest.main()
