import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('w43',Path(__file__).resolve().parents[1]/'scripts/workflow.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

class SecurityV43Tests(unittest.TestCase):
    def test_owned_boundary(self):
        self.assertTrue(w.task_owns('src/Api/a.cs',['src/Api/']))
        self.assertFalse(w.task_owns('src/ApiOther/a.cs',['src/Api/']))
    def test_empty_completion_blocked(self):
        data={'run_id':'demo','tasks':[{'id':'api','paths':['src/Api/'],'acceptance':['API tests pass'],'status':'ACTIVE','worktree':'/tmp/w','branch':'ai/demo/api','base':'a'}]}
        with patch.object(w,'load',return_value=data),patch.object(w.Path,'is_dir',return_value=True),patch.object(w,'git',side_effect=['','ai/demo/api','b']),patch.object(w,'changed_files',return_value=[]):
            with self.assertRaisesRegex(ValueError,'No committed changes'):w.complete('demo','api','verified change')
    def test_untrusted_command_blocked_before_execution(self):
        data={'run_id':'demo','tasks':[{'id':'api','paths':['src/Api/'],'acceptance':['API tests pass'],'status':'ACTIVE','worktree':'/tmp/w','branch':'ai/demo/api','base':'a'}]}
        with tempfile.TemporaryDirectory() as temp:
            commands=Path(temp)/'evil.json';commands.write_text('{"commands":[{"name":"evil","command_id":"shell","acceptance":["API tests pass"],"argv":["sh","-c","echo unsafe"]}]}')
            with patch.object(w,'load',return_value=data),patch.object(w.Path,'is_dir',return_value=True),patch.object(w,'git',side_effect=['ai/demo/api','','b']),patch.object(w,'changed_files',return_value=['src/Api/a.cs']):
                with self.assertRaisesRegex(ValueError,'trusted allowlist'):w.gate('demo',str(commands),True,'api')
    def test_missing_task_rejected(self):
        with self.assertRaisesRegex(ValueError,'explicit --task'):w.gate('demo','abc.json',True)
    def test_requires_permission(self):
        with self.assertRaisesRegex(ValueError,'--allow-exec'):w.gate('demo','abc.json',False,'api')

if __name__=='__main__':unittest.main()
