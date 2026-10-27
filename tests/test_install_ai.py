import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_ai import deploy, vetted_repo
ROOT=Path(__file__).resolve().parents[1]
class InstallerTests(unittest.TestCase):
 def test_preview_and_install_all(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)
   deploy(ROOT,target,['claude','codex','gemini','copilot'],dry_run=True)
   self.assertEqual(list(target.iterdir()),[])
   deploy(ROOT,target,['claude','codex','gemini','copilot'])
   for file in ['scripts/workflow.py','AGENTS.md','.ai/STATE.md','.claude/commands/uw-plan.md','.agents/skills/uw-plan/SKILL.md','.gemini/commands/uw-plan.toml','.github/prompts/uw-plan.prompt.md']:
    self.assertTrue((target/file).is_file(),file)
 def test_existing_state_and_policy_are_preserved_with_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)
   (target/'AGENTS.md').write_text('my original policy')
   (target/'.ai').mkdir()
   (target/'.ai/STATE.md').write_text('original state')
   deploy(ROOT,target,['gemini'],overwrite=True)
   self.assertEqual((target/'AGENTS.md').read_text(),'my original policy')
   self.assertEqual((target/'.ai/STATE.md').read_text(),'original state')
 def test_repo_url_validation(self):
  self.assertEqual(vetted_repo('https://github.com/salysat/Universal-AI-Workflow'), 'https://github.com/salysat/Universal-AI-Workflow')
  for u in ['https://token@github.com/salysat/repo','https://other.test/a/b','https://github.com/a','file:///tmp/test']:
   with self.assertRaises(ValueError):vetted_repo(u)
if __name__=='__main__':unittest.main()
