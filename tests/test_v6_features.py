import sys,unittest,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import uw_v6,uw_dashboard
class TestV6(unittest.TestCase):
    def test_extract(self):self.assertEqual(uw_v6.extract_json('```json\n{"a":1}\n```'),{'a':1})
    def test_usage(self):
        r=uw_v6.usage_of('{"usage":{"input_tokens":12,"output_tokens":8},"total_cost_usd":0.04}','claude')
        self.assertEqual(r['input_tokens'],12);self.assertEqual(r['cost_usd'],0.04)
    def test_no_invented_usage(self):self.assertIsNone(uw_v6.usage_of('{"message":"ok"}'))
    def test_stream_usage(self):self.assertEqual(uw_v6.usage_from_output('{"type":"thread.started"}\n{"type":"turn.completed","usage":{"input_tokens":99,"output_tokens":2}}','codex')['output_tokens'],2)
    def test_test_allowlist(self):
        with self.assertRaises(ValueError):uw_v6.guarded_test(['rm','-rf','/'],Path('.'),['python'])
    def test_dashboard(self):self.assertIn('runs',uw_dashboard.snapshot())
    def test_invalid_description(self):
        with self.assertRaises(ValueError):uw_v6.prepare_plan('demo','tiny','invalid',True,'out.json')
if __name__=='__main__':unittest.main()
