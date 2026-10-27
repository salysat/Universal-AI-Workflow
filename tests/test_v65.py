import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import uw_audit
import generate_commands

class NewV65Tests(unittest.TestCase):
    def test_sarif(self):
        sample={'version':'2.1.0','runs':[{'tool':{'driver':{'rules':[]}},'results':[{'ruleId':'SQL001','level':'error','message':{'text':'SQL injection'},'locations':[{'physicalLocation':{'artifactLocation':{'uri':'src/api.cs'}}}]}]}]}
        result=uw_audit.draft(sample,'audittest')
        self.assertEqual(len(result['tasks']),1)
        self.assertEqual(result['tasks'][0]['paths'],['src/api.cs'])
    def test_unsafe_path_is_excluded(self):
        report={'findings':[{'severity':'critical','path':'../secret','message':'bad'},{'severity':'high','path':'src/safe.cs','message':'issue'}]}
        out=uw_audit.draft(report,'audittest')
        self.assertEqual(len(out['excluded_findings']),1)
        self.assertEqual(len(out['tasks']),1)
    def test_low_severity_is_filtered(self):
        self.assertFalse(uw_audit.draft({'findings':[{'severity':'low','path':'src/f'}]},'audit')['tasks'])
    def test_commands_all_platforms_synchronized(self):
        self.assertEqual(generate_commands.generate(ROOT,check=True),[])
        registry=json.loads((ROOT/'commands/registry.json').read_text(encoding='utf8'))
        self.assertIn('uw-audit',registry['commands'])
        self.assertIn('uw-v6',registry['commands'])
        self.assertEqual(len(generate_commands.expected(ROOT)),len(registry['commands'])*6)
if __name__=='__main__': unittest.main()
