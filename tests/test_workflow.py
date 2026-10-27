import importlib.util
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'scripts/workflow.py'
s=importlib.util.spec_from_file_location('workflow',p)
w=importlib.util.module_from_spec(s);s.loader.exec_module(w)

class WorkflowTests(unittest.TestCase):
    def test_plan_valid(self):
        data={'run_id':'test','tasks':[{'id':'a','paths':['src/Api/'],'acceptance':['tests']},{'id':'b','paths':['src/Web/'],'acceptance':['build']} ]}
        self.assertIs(w.validate_plan(data),data)
    def test_overlap_rejected(self):
        data={'run_id':'test','tasks':[{'id':'a','paths':['src/'],'acceptance':['tests']},{'id':'b','paths':['src/Web/'],'acceptance':['build']}]}
        with self.assertRaises(ValueError):w.validate_plan(data)
    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):w.owner_path('../passwords')
    def test_ident(self):
        with self.assertRaises(ValueError):w.safe_ident('../../run')
    def test_hash_and_structure(self):
        w.validate()
    def test_missing_acceptance(self):
        with self.assertRaises(ValueError):w.validate_plan({'run_id':'a','tasks':[{'id':'x','paths':['src/'],'acceptance':[]}]})

if __name__=='__main__':unittest.main()
