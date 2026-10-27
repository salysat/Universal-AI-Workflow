import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import auto_runner

class AutoRunnerTests(unittest.TestCase):
    def setUp(self):
        self.plan={'run_id':'test_run','tasks':[{'id':'one','status':'PLANNED','paths':['src/a'],'acceptance':['test-a'],'agent':'demo-safe'},{'id':'two','status':'ACTIVE','paths':['src/b'],'acceptance':['test-b']} ]}
    @patch.object(auto_runner.workflow,'load')
    def test_preview_assignments(self,load):
        load.return_value=self.plan
        got=auto_runner.describe('test_run','demo-safe',2)
        self.assertEqual([v['agent'] for v in got['assignments']],['demo-safe','demo-safe'])
    @patch.object(auto_runner.agent_runner,'load_config')
    @patch.object(auto_runner.workflow,'load')
    def test_no_execution_without_approval(self,load,config):
        load.return_value=self.plan
        config.return_value={'agents':{'demo-safe':{}}}
        with patch.object(auto_runner.workflow,'worktree') as wt,patch.object(auto_runner.agent_runner,'run_one') as agent:
            self.assertIsNone(auto_runner.execute('test_run','demo-safe','x',2,False,False))
            wt.assert_not_called();agent.assert_not_called()
    @patch.object(auto_runner.workflow,'load')
    def test_invalid_worker_count(self,load):
        with self.assertRaisesRegex(ValueError,'max-workers'):
            auto_runner.execute('test_run','demo-safe','x',0,False,False)
        load.assert_not_called()
    @patch.object(auto_runner.workflow,'load')
    @patch.object(auto_runner.agent_runner,'load_config')
    def test_unknown_agent_rejected(self,config,load):
        load.return_value=self.plan
        config.return_value={'agents':{'different':{}}}
        with self.assertRaisesRegex(ValueError,'not configured'):
            auto_runner.execute('test_run','demo-safe','x',1,True,True)

if __name__=='__main__':unittest.main()
