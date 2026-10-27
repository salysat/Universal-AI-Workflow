import sys,unittest,tempfile
try:
    import tomllib  # standard library in Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # third-party fallback for Python 3.10
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_commands import ROOT,PLATFORMS,install
class CommandTests(unittest.TestCase):
 def test_file_formats_and_names(self):
  for name in ('uw-help','uw-plan','uw-build','uw-agents','uw-ship'):
   for platform,folder in PLATFORMS.items():
    ext='.toml' if platform=='gemini' else '.prompt.md' if platform=='copilot' else '.md'
    p=ROOT/folder/name/( 'SKILL.md') if platform=='codex' else ROOT/folder/(name+ext)
    self.assertTrue(p.exists(),str(p))
   with (ROOT/'.gemini/commands'/f'{name}.toml').open('rb') as f:self.assertIn('prompt',tomllib.load(f))
 def test_install_safe_and_dry_run(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)
   plan,_=install(target,['gemini'],dry_run=True)
   self.assertGreater(plan,0)
   self.assertEqual(list(target.rglob('*')),[])
   install(target,['gemini'])
   cmd=target/'.gemini/commands/uw-plan.toml'
   cmd.write_text('custom local command')
   install(target,['gemini'])
   self.assertEqual(cmd.read_text(),'custom local command')
   install(target,['gemini'],overwrite=True)
   self.assertIn('prompt',cmd.read_text())
if __name__=='__main__':unittest.main()
