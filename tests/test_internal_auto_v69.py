import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'uw_internal_auto.py'
spec = importlib.util.spec_from_file_location('uw_internal_auto', SCRIPT)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class InternalAutoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(u, 'BASE', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.run = 'sample'
        folder = self.root / '.ai/runs/sample'
        folder.mkdir(parents=True)
        u.write(folder / 'plan.json', {'run_id': 'sample', 'tasks': [
            {'id': 'first', 'acceptance': ['build passes'], 'depends_on': []},
            {'id': 'second', 'acceptance': ['tests pass'], 'depends_on': ['first']}]})

    def test_dependencies_and_evidence(self):
        u.initialize(self.run)
        self.assertEqual([x['task_id'] for x in u.next_task(self.run)['ready']], ['first'])
        with self.assertRaises(ValueError): u.record(self.run, 'second', 'architect', 'planned')
        for role in u.ROLES:
            u.record(self.run, 'first', role, 'checked by ' + role, approved=(role == 'reviewer'))
        self.assertEqual(u.next_task(self.run)['ready'][0]['task_id'], 'second')
        self.assertEqual(u.state(self.run)[0]['tasks']['first']['status'], 'COMPLETED')

    def test_no_empty_evidence_or_out_of_order(self):
        u.initialize(self.run)
        with self.assertRaises(ValueError): u.record(self.run, 'first', 'developer', 'x')
        with self.assertRaises(ValueError): u.record(self.run, 'first', 'architect', ' ')

    def test_failed_review_resets_tests(self):
        u.initialize(self.run)
        for role in u.ROLES: u.record(self.run, 'first', role, role, approved=False)
        s = u.state(self.run)[0]['tasks']['first']
        self.assertEqual(s['role'], 'developer')
        self.assertNotIn('tester', s['evidence'])
        u.record(self.run, 'first', 'developer', 'fix')
        u.record(self.run, 'first', 'tester', 'rerun')
        u.record(self.run, 'first', 'reviewer', 'verified', approved=True)
        self.assertEqual(u.state(self.run)[0]['tasks']['first']['status'], 'COMPLETED')

    def test_plan_change_refused(self):
        u.initialize(self.run)
        p = u.safe_run(self.run) / 'plan.json'
        d = u.read(p); d['tasks'][0]['acceptance'] = ['changed']; u.write(p, d)
        with self.assertRaisesRegex(ValueError, 'Plan changed'): u.state(self.run)

    def test_missing_and_cycle(self):
        p = u.safe_run(self.run) / 'plan.json'; d = u.read(p)
        d['tasks'][0]['depends_on'] = ['second']; u.write(p, d)
        with self.assertRaisesRegex(ValueError, 'cycle'): u.plan(self.run)

    def test_report_and_resume(self):
        u.initialize(self.run)
        u.record(self.run, 'first', 'architect', 'scope')
        self.assertEqual(u.next_task(self.run)['ready'][0]['role'], 'developer')
        self.assertTrue(Path(u.markdown(self.run)['report']).exists())
        self.assertEqual(u.initialize(self.run)['tasks']['first']['role'], 'developer')

    def test_block(self):
        u.initialize(self.run)
        u.block(self.run, 'first', 'needs credentials')
        self.assertEqual(u.next_task(self.run)['ready'], [])

if __name__ == '__main__': unittest.main()
