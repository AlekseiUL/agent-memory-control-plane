import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from amcp.core import ControlPlane, PolicyDenied
from amcp import mcp_adapter as mcp


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cp = ControlPlane(Path(self.tmp.name) / 'db')
        self.cp.init()

    def candidate(self, private=False):
        return self.cp.propose('private' if private else 'public', 'shared searchable fact',
                               'profile-memory' if private else 'public-knowledge',
                               'assistant' if private else 'researcher',
                               'private' if private else 'public',
                               actor='assistant' if private else 'researcher', apply=True)['candidate_id']

    def test_payload_cannot_grant_authority(self):
        self.cp.promote(self.candidate(True), apply=True)
        with self.assertRaises((PolicyDenied, ValueError)):
            mcp.call(self.cp, 'memory_search', {'query': 'searchable', 'actor': 'dispatcher'})

    def test_default_cannot_promote(self):
        cid = self.candidate()
        with self.assertRaises((PolicyDenied, ValueError)):
            mcp.call(self.cp, 'memory_promote', {'candidate_id': cid, 'apply': True})
        self.assertEqual(self.cp.audit()['counts']['records'], 0)

    def test_default_is_read_only(self):
        with self.assertRaises((PolicyDenied, ValueError)):
            mcp.call(self.cp, 'memory_propose', {'key': 'k', 'content': 'fact', 'apply': True})

    def test_acl_before_limit_stable(self):
        self.cp.promote(self.candidate(True), apply=True)
        public = self.cp.promote(self.candidate(), apply=True)['record_id']
        for _ in range(2):
            self.assertEqual([r['record_id'] for r in self.cp.search('searchable', limit=1)], [public])
        self.assertEqual(self.cp.search('searchable', actor='unknown'), [])

    def test_notifications_never_respond_or_mutate(self):
        cid = self.candidate()
        for method, params in [('notifications/initialized', {}), ('unknown', {}),
                               ('tools/call', {'name': 'memory_promote', 'arguments': {'candidate_id': cid, 'apply': True}})]:
            self.assertIsNone(mcp.dispatch(self.cp, {'jsonrpc': '2.0', 'method': method, 'params': params}))
        self.assertEqual(self.cp.audit()['counts']['records'], 0)

    def test_error_keeps_id(self):
        out = io.StringIO()
        req = {'jsonrpc': '2.0', 'id': 'request-7', 'method': 'tools/call', 'params': {'name': 'memory_search', 'arguments': {}}}
        with patch('sys.stdin', io.StringIO(json.dumps(req)+'\n')), patch('sys.stdout', out):
            mcp.main(['--db', str(self.cp.db_path)])
        self.assertEqual(json.loads(out.getvalue())['id'], 'request-7')

    def test_schema_and_default_surface(self):
        tools = mcp.dispatch(self.cp, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['result']['tools']
        self.assertNotIn('memory_promote', [t['name'] for t in tools])
        for tool in tools:
            schema = tool['inputSchema']
            self.assertIn('properties', schema)
            self.assertFalse(schema['additionalProperties'])
        search = next(t for t in tools if t['name'] == 'memory_search')
        self.assertIn('query', search['inputSchema']['required'])

    def test_self_approval_is_denied(self):
        c = self.cp.propose('team', 'team fact', 'governance', 'dispatcher', 'team', actor='dispatcher', apply=True)
        with self.assertRaises(PolicyDenied):
            self.cp.promote(c['candidate_id'], reviewer='dispatcher', apply=True)

    def test_trusted_context_separates_proposer_and_reviewer(self):
        proposer = mcp.Identity('assistant', can_propose=True)
        c = mcp.call(self.cp, 'memory_propose', {'key': 'new', 'content': 'stable fact', 'apply': True}, proposer)
        with self.assertRaises(PolicyDenied):
            mcp.call(self.cp, 'memory_promote', {'candidate_id': c['candidate_id'], 'apply': True}, proposer)
        reviewer = mcp.Identity('reviewer', can_promote=True)
        result = mcp.call(self.cp, 'memory_promote', {'candidate_id': c['candidate_id'], 'apply': True}, reviewer)
        self.assertEqual(result['decision'], 'promote')

    def test_invalid_types_rejected(self):
        for args in [{'query': 1}, {'query': 'fact', 'limit': True}, {'query': 'fact', 'limit': -1}]:
            with self.assertRaises(ValueError): mcp.call(self.cp, 'memory_search', args)


if __name__ == '__main__':
    unittest.main()
