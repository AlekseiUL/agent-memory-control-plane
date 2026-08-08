import json, unittest
from importlib.resources import files
from amcp.policy import load_policy

class ResourceTests(unittest.TestCase):
    def test_policy_is_packaged_and_fail_closed(self):
        policy=load_policy(); self.assertFalse(policy["promotion"]["auto_merge"]); self.assertFalse(policy["promotion"]["auto_delete"])
    def test_all_schemas_parse(self):
        root=files("amcp").joinpath("resources","schemas"); schemas=list(root.iterdir()); self.assertEqual(len(schemas),7)
        for path in schemas:
            schema=json.loads(path.read_text()); self.assertEqual(schema["type"],"object"); self.assertTrue(schema["required"])

if __name__=="__main__": unittest.main()
