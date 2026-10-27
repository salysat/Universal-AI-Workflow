import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'agent_runner.py'
spec=importlib.util.spec_from_file_location('agent_runner',SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class RunnerTests(unittest.TestCase):
    def test_sample_config(self):
        self.assertIn('demo-safe',mod.load_config(SCRIPT.parents[1]/'examples'/'agents.example.json')['agents'])
    def test_boundary(self):
        self.assertTrue(mod.allowed('src/Api/test.cs',['src/Api/']))
        self.assertFalse(mod.allowed('src/ApiEvil/x.cs',['src/Api/']))
        self.assertFalse(mod.allowed('other/file.cs',['src/Api/']))
    def test_template_rejects_unapproved(self):
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'agents.json'
            p.write_text(json.dumps({'version':1,'agents':{'bad':{'argv':['echo','{secret}']}}}))
            with self.assertRaises(ValueError):mod.load_config(p)
    def test_requires_approval(self):
        with self.assertRaises(ValueError):mod.run_one('demo','api','demo-safe','x',False)

if __name__=='__main__':unittest.main()
