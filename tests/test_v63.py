import json, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import agent_runner, uw_v6

class V63Tests(unittest.TestCase):
    def test_v6_stdin_transport(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Path(d)/'config.json'
            cfg.write_text(json.dumps({'version':1,'agents':{'local':{'argv':[sys.executable,'-c','import sys;print(sys.stdin.read())'],'prompt_transport':'stdin'}},'roles':{'architect':'local'}}))
            result=uw_v6.call_cli(str(cfg),'architect','تجربة stdin',d)
            self.assertEqual(result['exit_code'],0)
            self.assertIn('تجربة stdin',result['stdout'])
            self.assertNotIn('?????', result['stdout'])
            self.assertFalse(list(Path(d).glob('uw-v6-*')))
    def test_v6_file_transport_inside_worktree(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Path(d)/'config.json'
            cfg.write_text(json.dumps({'version':1,'agents':{'local':{'argv':[sys.executable,'-c','import pathlib,sys; p=pathlib.Path(sys.argv[1]);print(str(p.parent.parent));print(p.read_text())','{prompt_file}'],'prompt_transport':'file'}},'roles':{'reviewer':'local'}}))
            result=uw_v6.call_cli(str(cfg),'reviewer','file prompt',d)
            self.assertEqual(result['exit_code'],0)
            self.assertIn(d,result['stdout'])
            self.assertIn('file prompt',result['stdout'])
    def test_config_rejects_bad_transport(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Path(d)/'config.json'
            cfg.write_text(json.dumps({'version':1,'agents':{'x':{'argv':['python'],'prompt_transport':'pipe_to_shell'}}}))
            with self.assertRaises(ValueError):agent_runner.load_config(cfg)
    def test_json_arg_not_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Path(d)/'config.json'
            cfg.write_text(json.dumps({'version':1,'agents':{'x':{'argv':['python','-c','print({"a":1})']}}}))
            self.assertIn('x',agent_runner.load_config(cfg)['agents'])
