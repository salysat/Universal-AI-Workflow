import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import workflow,uw_v6,install_ai

class RegressionV61(unittest.TestCase):
    def test_task_hash_ignores_status(self):
        task={'id':'api','paths':['api'],'acceptance':['ok'],'status':'ACTIVE','head':'abc'}
        h=workflow.task_hash(task)
        task.update(status='DONE',head='def',gate_results=[])
        self.assertEqual(h,workflow.task_hash(task))
        task['acceptance']=['new']
        self.assertNotEqual(h,workflow.task_hash(task))
    def test_installer_contains_v6(self):
        self.assertIn('scripts/uw_v6.py',install_ai.RUNTIME_FILES)
        self.assertIn('scripts/uw_dashboard.py',install_ai.RUNTIME_FILES)
    def test_reviewer_rejects_empty_committed_diff(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)
            info={'base':'HEAD','acceptance':['build'],'worktree':str(t)}
            with patch.object(uw_v6.agent_runner,'task_info',return_value=(info,t)),patch.object(uw_v6.subprocess,'run') as sp:
                import subprocess
                sp.side_effect=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,b'',b'')]
                with self.assertRaisesRegex(ValueError,'empty committed diff'):
                    uw_v6.independent_review('demo','api','unused',True)
    def test_installer_gitignore(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)
            with patch('install_ai.install',return_value=None):
                install_ai.deploy(ROOT,target,['claude'])
            val=(target/'.gitignore').read_text()
            self.assertIn('.ai/runs/',val)
            self.assertIn('__pycache__/',val)
            self.assertTrue((target/'scripts/uw_v6.py').exists())
if __name__=='__main__':unittest.main()
