"""Tests for the drop-in context guard. Run with:
python -m unittest discover -s tests -q
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SCRIPT = KIT / 'scripts' / 'uw_context_guard.py'
spec = importlib.util.spec_from_file_location('uw_context_guard', SCRIPT)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / '.ai' / 'runs' / 'demo'
        folder.mkdir(parents=True)
        plan = {'run_id': 'demo', 'tasks': [
            {'id': 'T1', 'description': 'first', 'paths': ['src/A/'],
             'acceptance': ['build passes', 'HTTP check passes']},
            {'id': 'T2', 'description': 'second', 'paths': ['src/B/'],
             'acceptance': ['tests pass'], 'depends_on': ['T1']}]}
        (folder / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
        state = {'schema': 1, 'run_id': 'demo', 'tasks': {
            'T1': {'status': 'IN_PROGRESS', 'role': 'tester', 'depends_on': [],
                   'acceptance': ['build passes', 'HTTP check passes'],
                   'evidence': {'architect': {'details': 'scope', 'timestamp': '2026-10-27T00:00:00'},
                                'developer': {'details': 'diff', 'timestamp': '2026-10-27T00:01:00'},
                                'tester': {'details': 'OK ' * 500 + 'exit 0', 'timestamp': '2026-10-27T00:02:00'}},
                   'attempts': 0},
            'T2': {'status': 'PLANNED', 'role': 'architect', 'depends_on': ['T1'],
                   'acceptance': ['tests pass'], 'evidence': {}, 'attempts': 0}}}
        (folder / 'internal-auto.json').write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        (folder / 'big.log').write_text('x' * 40000, encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('# rules\n', encoding='utf-8')
        self.folder = folder

    def test_brief_is_compact(self):
        b = g.brief(self.root, 'demo')
        self.assertEqual(b['current']['task_id'], 'T1')
        self.assertEqual(b['current']['role'], 'tester')
        self.assertNotIn('evidence', b)
        self.assertLess(len(json.dumps(b, ensure_ascii=False)), 2500)
        self.assertLessEqual(len(b['last_verification']), 210)
        self.assertIn('uw_internal_auto.py', b['current']['next_command'])

    def test_prompt_bounded_and_resumable(self):
        r = g.fresh_prompt(self.root, 'demo')
        text = (self.root / r['prompt']).read_text(encoding='utf-8')
        self.assertLessEqual(r['words'], 450)
        self.assertIn('demo', text)
        self.assertIn('T1', text)
        self.assertIn('internal-auto.json', text)

    def test_check_budget(self):
        over = g.check(self.root, 'demo', 1)
        under = g.check(self.root, 'demo', 10 ** 9)
        self.assertTrue(over['over_budget'])
        self.assertFalse(under['over_budget'])
        self.assertTrue(any('big.log' in x['file'] for x in over['top']))
        self.assertEqual(g.main(['--root', str(self.root), 'check', '--run', 'demo', '--max-tokens', '1']), 2)

    def test_trim_preview_and_apply(self):
        before = (self.folder / 'internal-auto.json').read_text(encoding='utf-8')
        preview = g.trim(self.root, 'demo', 200, apply=False)
        self.assertTrue(preview['changes'])
        self.assertEqual((self.folder / 'internal-auto.json').read_text(encoding='utf-8'), before)
        self.assertFalse((self.folder / 'internal-auto.full.json').exists())
        applied = g.trim(self.root, 'demo', 200, apply=True)
        self.assertTrue(applied['apply'])
        self.assertTrue((self.folder / 'internal-auto.full.json').is_file())
        state = json.loads((self.folder / 'internal-auto.json').read_text(encoding='utf-8'))
        full = json.loads((self.folder / 'internal-auto.full.json').read_text(encoding='utf-8'))
        self.assertLess(len(state['tasks']['T1']['evidence']['tester']['details']), 400)
        self.assertGreater(len(full['tasks']['T1']['evidence']['tester']['details']), 1000)
        self.assertEqual(state['tasks']['T1']['acceptance'], full['tasks']['T1']['acceptance'])

    def test_check_excludes_prompt_and_backup(self):
        g.fresh_prompt(self.root, 'demo')
        g.trim(self.root, 'demo', 200, apply=True)
        names = [rel for rel, _ in g.context_files(self.root, 'demo')]
        self.assertFalse(any(n.endswith('FRESH_PROMPT.md') for n in names))
        self.assertFalse(any(n.endswith('.full.json') for n in names))

    def test_output_path_cannot_escape(self):
        with self.assertRaises(ValueError):
            g.fresh_prompt(self.root, 'demo', output='../escape.md')


if __name__ == '__main__':
    unittest.main()
