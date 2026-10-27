"""Tests for the one-word uw-auto autopilot and local skill routing."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ua = load('uw_autopilot')
sr = load('uw_skill_router')
ar = load('agent_runner')
wf = load('workflow')
guard = load('uw_context_guard')


def make_root(base):
    base = Path(base)
    (base / '.gitignore').write_text('.ai/runs/\n.ai/worktrees/\n', encoding='utf-8')
    (base / 'AGENTS.md').write_text('# rules\n', encoding='utf-8')
    (base / '.ai' / 'HANDOFF.md').parent.mkdir(parents=True, exist_ok=True)
    (base / '.ai' / 'HANDOFF.md').write_text('# handoff\n', encoding='utf-8')
    (base / 'src').mkdir()
    for i in range(4):
        (base / 'src' / f'f{i}.py').write_text('x = 1\n', encoding='utf-8')
    (base / 'lib').mkdir()
    for i in range(4):
        (base / 'lib' / f'g{i}.js').write_text('let x = 1;\n', encoding='utf-8')
    reg = {'version': 1, 'commands': {
        'uw-build': {'description': 'Build', 'body': 'x'},
        'uw-test': {'description': 'Test', 'body': 'x'},
        'uw-context': {'description': 'Context budget and fresh-session handoff', 'body': 'x'}}}
    (base / 'commands').mkdir()
    (base / 'commands' / 'registry.json').write_text(json.dumps(reg), encoding='utf-8')
    for name in reg['commands']:
        p = base / '.agents' / 'skills' / name
        p.mkdir(parents=True)
        (p / 'SKILL.md').write_text('---\nname: ' + name + '\n---\nbody\n', encoding='utf-8')
    (base / '.ai' / 'skills').mkdir(parents=True, exist_ok=True)
    (base / '.ai' / 'skills' / 'REGISTRY.json').write_text(json.dumps({
        'schema_version': '4.0', 'skills': []}), encoding='utf-8')
    return base


class AutopilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_root(self.tmp.name)
        self.patcher = patch.object(ua, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def cfg(self, **over):
        cfg = dict(ua.DEFAULTS)
        cfg.update(over)
        return cfg

    def test_heuristic_plan_is_valid_and_dependency_closed(self):
        plan = ua.heuristic_plan('demo', 'fix tests and build', 3)
        self.assertIs(wf.validate_plan(plan), plan)
        ids = {t['id'] for t in plan['tasks']}
        verify = [t for t in plan['tasks'] if t['id'] == 'VERIFY'][0]
        self.assertEqual(set(verify['depends_on']), ids - {'VERIFY'})
        owners = [p for t in plan['tasks'] for p in t['paths']]
        self.assertEqual(len(owners), len(set(owners)))

    def test_skill_route_is_local_only(self):
        task = {'id': 'T1', 'description': 'fix failing build and tests',
                'acceptance': ['build passes', 'tests pass'], 'paths': ['src/']}
        r = sr.route(self.root, task)
        self.assertFalse(r['network_used'])
        self.assertFalse(r['auto_install'])
        self.assertTrue(r['skills'])
        self.assertTrue(all(Path(self.root, s['path']).is_file() for s in r['skills']))
        self.assertIn('Read these', sr.prompt_block(r))

    def test_vendored_skill_needs_pinned_hash_and_approval(self):
        skill = self.root / '.ai' / 'skills' / 'extra.md'
        skill.write_text('reviewed local skill\n', encoding='utf-8')
        good = sr.sha256(skill)
        data = {'schema_version': '4.0', 'skills': [{
            'id': 'extra', 'path': '.ai/skills/extra.md', 'sha256': '0' * 64,
            'review_status': 'approved', 'approved_for_execution': True,
            'review_expires': '2999-01-01', 'triggers': ['migrate database']}]}
        (self.root / '.ai' / 'skills' / 'REGISTRY.json').write_text(json.dumps(data), encoding='utf-8')
        task = {'id': 'T1', 'description': 'migrate database schema', 'acceptance': [], 'paths': ['src/']}
        self.assertFalse(any(s['id'] == 'extra' for s in sr.route(self.root, task)['skills']))
        data['skills'][0]['sha256'] = good
        (self.root / '.ai' / 'skills' / 'REGISTRY.json').write_text(json.dumps(data), encoding='utf-8')
        self.assertTrue(any(s['id'] == 'extra' for s in sr.route(self.root, task)['skills']))
        data['skills'][0]['approved_for_execution'] = False
        (self.root / '.ai' / 'skills' / 'REGISTRY.json').write_text(json.dumps(data), encoding='utf-8')
        self.assertFalse(any(s['id'] == 'extra' for s in sr.route(self.root, task)['skills']))

    def test_extra_skill_requires_hash_and_cannot_escape_root(self):
        skill = self.root / '.ai' / 'skills' / 'mine.md'
        skill.write_text('mine\n', encoding='utf-8')
        extra = [{'id': 'mine', 'path': '.ai/skills/mine.md', 'sha256': sr.sha256(skill),
                  'approved': True, 'triggers': ['specialwidget']}]
        task = {'id': 'T1', 'description': 'specialwidget work', 'acceptance': [], 'paths': ['src/']}
        self.assertTrue(any(s['id'] == 'mine' for s in sr.route(self.root, task, extra_skills=extra)['skills']))
        bad = [{'id': 'evil', 'path': '../outside.md', 'sha256': 'a' * 64, 'approved': True,
                'triggers': ['specialwidget']}]
        self.assertFalse(any(s['id'] == 'evil' for s in sr.route(self.root, task, extra_skills=bad)['skills']))

    def test_init_config_is_safe_by_default(self):
        path = self.root / 'uw-auto.config.json'
        ua.init_config(str(path))
        cfg = json.loads(path.read_text(encoding='utf-8'))
        self.assertFalse(cfg['approve_agents'])
        self.assertFalse(cfg['approve_worktrees'])
        self.assertIn('uw-auto.config.json', (self.root / '.gitignore').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            ua.init_config(str(path))

    def test_boot_creates_plan_mission_and_compact_output(self):
        result = ua.boot(self.cfg(run_id='run1'), 'run1')
        self.assertTrue(result['plan_created'])
        self.assertEqual(result['mode'], 'sessions')
        self.assertIsNotNone(result['current'])
        self.assertTrue(result['no_external_assistant'])
        mission = (self.root / '.ai' / 'runs' / 'run1' / 'MISSION.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(mission.split()), 450)
        self.assertIn('Never load into chat', mission)
        self.assertLess(len(json.dumps(result)), 3000)
        self.assertIn('sessions', result)
        self.assertTrue(ua.run_dir('run1').joinpath('SPAWN.md').is_file())
        self.assertTrue(ua.run_dir('run1').joinpath('plan.json').is_file())

    def test_tick_advances_and_forces_new_chat_when_over_budget(self):
        cfg = self.cfg(run_id='run1', max_tokens=1)
        ua.boot(cfg, 'run1')
        out = ua.tick(cfg, 'run1', 'T01', 'done', 'build ok, log at build.log')
        self.assertEqual(out['task'], 'T01')
        self.assertEqual(out['status'], 'DONE')
        self.assertTrue(out['next_chat_required'])
        self.assertTrue((self.root / out['fresh_prompt']).is_file())

    def test_run_without_approval_stays_inhost_and_executes_nothing(self):
        cfg = self.cfg(run_id='run1')
        ua.boot(cfg, 'run1')
        out = ua.run_tasks(cfg, 'run1', 2)
        self.assertEqual(out['mode'], 'sessions')
        self.assertEqual(out['executed'], 0)
        self.assertTrue(out['no_external_assistant'])
        self.assertIn('spawn', out['action'])

    def test_boot_is_idempotent_and_status_reads_state(self):
        cfg = self.cfg(run_id='run1')
        first = ua.boot(cfg, 'run1')
        second = ua.boot(cfg, 'run1')
        self.assertTrue(first['plan_created'])
        self.assertFalse(second['plan_created'])
        self.assertEqual(first['current'], second['current'])
        state = json.loads((ua.run_dir('run1') / 'autopilot.json').read_text(encoding='utf-8'))
        self.assertEqual(set(state['tasks']), {'T01', 'T02', 'VERIFY'})


    def test_self_mode_creates_multiple_independent_session_packets(self):
        cfg = self.cfg(run_id='run1', host_subagents=True, parallel_sessions=2)
        result = ua.boot(cfg, 'run1')
        self.assertEqual(result['mode'], 'self')
        self.assertEqual(len(result['sessions']), 2)
        for s in result['sessions']:
            path = self.root / s['file']
            self.assertTrue(path.is_file())
            self.assertLessEqual(s['words'], 450)
            body = path.read_text(encoding='utf-8')
            self.assertIn(s['task'], body)
            self.assertIn('uw_autopilot.py tick', body)
            self.assertIn('لا مساعدات', body)
        spawn = (ua.run_dir('run1') / 'SPAWN.md').read_text(encoding='utf-8')
        self.assertIn('native subagents', spawn)
        self.assertIn('نفسك', spawn)

    def test_spawn_command_is_compact_and_uses_no_external_assistant(self):
        cfg = self.cfg(run_id='run1', host_subagents=True, parallel_sessions=2)
        ua.boot(cfg, 'run1')
        out = ua.spawn(cfg, 'run1')
        self.assertEqual(out['mode'], 'self')
        self.assertTrue(out['no_external_assistant'])
        self.assertEqual(len(out['sessions']), 2)
        self.assertIn('spawn', out['next_wave'])
        self.assertLess(len(json.dumps(out)), 3000)

    def test_external_cli_is_disabled_even_if_flags_are_true(self):
        cfg = self.cfg(run_id='run1', approve_agents=True, approve_worktrees=True,
                       external_enabled=False)
        env = ua.environment(cfg)
        self.assertFalse(env['external_available'])
        self.assertNotEqual(env['mode'], 'external')
        result = ua.boot(cfg, 'run1')
        self.assertTrue(result['no_external_assistant'])

    def test_mode_override_and_bad_override_are_handled(self):
        cfg = self.cfg(run_id='run1', mode_override='self')
        self.assertEqual(ua.environment(cfg)['mode'], 'self')
        path = self.root / 'bad.json'
        path.write_text(json.dumps({'version': 1, 'mode_override': 'nonsense'}), encoding='utf-8')
        with self.assertRaises(ValueError):
            ua.load_config(str(path))

    def test_tick_regenerates_the_next_session_packet(self):
        cfg = self.cfg(run_id='run1')
        ua.boot(cfg, 'run1')
        out = ua.tick(cfg, 'run1', 'T01', 'done', 'build ok; log at build.log')
        self.assertTrue(out['spawn_again'])
        self.assertTrue(out['next_chat_required'])
        self.assertEqual(out['next'], 'T02')
        self.assertTrue(any(s['task'] == 'T02' for s in out['sessions']))
        self.assertTrue((self.root / out['spawn_file']).is_file())

    def test_session_packet_refuses_oversized_content(self):
        task = {'id': 'T1', 'description': 'word ' * 1000, 'paths': ['src/'],
                'acceptance': ['a'], 'role': 'developer'}
        state = {'schema': ua.SCHEMA, 'run_id': 'big', 'tasks': {
            'T1': {'status': 'PLANNED', 'role': 'developer', 'depends_on': [],
                   'skills': [], 'attempts': 0}}}
        ua.atomic_json(ua.run_dir('big') / 'autopilot.json', state)
        with self.assertRaises(ValueError):
            ua.session_packet('big', task, state['tasks']['T1'], 1)

    def test_agent_prompt_can_carry_routed_skills(self):
        task = {'id': 'T1', 'paths': ['src/'], 'acceptance': ['build passes'], 'description': 'x'}
        p = ar.prompt_for(task, 'r', 'T1', 'Read .agents/skills/uw-build/SKILL.md')
        self.assertIn('Read .agents/skills/uw-build/SKILL.md', p)
        self.assertIn('Acceptance criteria', p)


if __name__ == '__main__':
    unittest.main()
