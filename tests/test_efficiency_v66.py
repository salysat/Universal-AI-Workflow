import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('uw_efficiency',P/'scripts/uw_efficiency.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class EfficiencyTests(unittest.TestCase):
    def test_snapshot_and_drift(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'one.txt';f.write_text('abc')
            snap=m.snapshot(['one.txt'],d)
            self.assertTrue(m.verify(snap,d)['ok'])
            f.write_text('abcd')
            self.assertEqual(m.verify(snap,d)['results']['one.txt'],'CHANGED')
    def test_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): m.within(d,'../secret')
    def test_context_budget(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'a.txt').write_text('a'*100)
            r=m.budget(['a.txt'],d,10)
            self.assertFalse(r['files'][0]['included'])
    def test_magic(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'weird.bin';f.write_bytes(b'%PDF-1.7\n')
            self.assertEqual(m.detect_type(f),'pdf')
    def test_provider_nonintrusive(self):
        r=m.provider_health()
        self.assertEqual(r['codex']['authenticated'],'NOT_CHECKED')
    def test_skills_not_auto_exec(self):
        r=m.skill_route('user asks to find a skill')
        self.assertTrue(all(x['action']=='SUGGEST_ONLY' for x in r))
    def test_handoff_initial_incomplete(self):
        self.assertFalse(m.handoff_check()['ok'])
    def test_usage_append(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'usage.jsonl'
            m.add_usage(p,'codex',10,20,'demo')
            self.assertEqual(json.loads(p.read_text())['output_tokens'],20)
            with self.assertRaises(ValueError):m.add_usage(p,'codex',-1,2,'demo')
if __name__=='__main__':unittest.main()
