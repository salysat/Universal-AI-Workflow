import sys,os,tempfile,subprocess,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import agent_runner,workflow,uw_dashboard
class V62Tests(unittest.TestCase):
    def test_environment_does_not_leak(self):
        os.environ['MY_SECRET_API_KEY']='sensitive'
        try:
            env=agent_runner.safe_agent_env({'AIWF_TASK_ID':'test'})
            self.assertNotIn('MY_SECRET_API_KEY',env)
            self.assertEqual(env['AIWF_TASK_ID'],'test')
        finally:del os.environ['MY_SECRET_API_KEY']
    def test_arabic_paths(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['git','init','-q',d],check=True)
            Path(d,'ملف.txt').write_text('hello')
            self.assertIn('ملف.txt',agent_runner.porcelain_paths(d))
    def test_renamed_paths(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['git','init','-q',d],check=True)
            subprocess.run(['git','-C',d,'config','user.email','test@example.com'],check=True)
            subprocess.run(['git','-C',d,'config','user.name','Test'],check=True)
            Path(d,'قديم.txt').write_text('hello')
            subprocess.run(['git','-C',d,'add','.'],check=True)
            subprocess.run(['git','-C',d,'commit','-qm','initial'],check=True)
            subprocess.run(['git','-C',d,'mv','قديم.txt','جديد.txt'],check=True)
            self.assertEqual(set(agent_runner.porcelain_paths(d)),{'قديم.txt','جديد.txt'})
    def test_gate_new_commands(self):
        self.assertIn('go-test',workflow.SAFE_COMMANDS)
        self.assertIn('npm-run-build',workflow.SAFE_COMMANDS)
    def test_dashboard_host_guard_present(self):
        import inspect
        self.assertIn('Untrusted Host',inspect.getsource(uw_dashboard.Handler.do_GET))
if __name__=='__main__':unittest.main()
