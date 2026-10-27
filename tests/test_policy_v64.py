import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.workflow import resolve_gate_commands

class PolicyTests(unittest.TestCase):
    def test_approved_policy_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'policy.json'
            c=Path(d)/'commands.json'
            p.write_text(json.dumps({'commands':{'custom-check':['python','-m','unittest']}}))
            c.write_text(json.dumps({'commands':[{'name':'check','command_id':'custom-check'}]}))
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            items, allowed=resolve_gate_commands(c,p,digest)
            self.assertEqual(allowed['custom-check'],['python','-m','unittest'])
            p.write_text(p.read_text()+' ')
            with self.assertRaises(ValueError):resolve_gate_commands(c,p,digest)
    def test_no_unpinned_policy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'policy.json'; c=Path(d)/'commands.json'
            p.write_text('{"commands":{"x-check":["python"]}}');c.write_text('{"commands":[]}')
            with self.assertRaises(ValueError):resolve_gate_commands(c,p,None)
    def test_cannot_override_fixed_commands(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'policy.json'; c=Path(d)/'commands.json'
            p.write_text('{"commands":{"python-version":["evil"]}}');c.write_text('{"commands":[]}')
            with self.assertRaises(ValueError):resolve_gate_commands(c,p,hashlib.sha256(p.read_bytes()).hexdigest())
