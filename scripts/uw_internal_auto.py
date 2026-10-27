#!/usr/bin/env python3
"""In-host workflow scheduler. Does not invoke models, processes, git or arbitrary tests.

The invoking assistant performs each stage using its native capabilities and records evidence.
Storage is confined to .ai/runs/<id>/internal-auto.json. State writes are atomic.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import tempfile

BASE = Path(__file__).resolve().parents[1]
IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
ROLES = ('architect', 'developer', 'tester', 'reviewer')


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_run(run):
    if not IDENT.fullmatch(run):
        raise ValueError('Invalid run ID')
    return BASE / '.ai' / 'runs' / run


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
        temporary = handle.name
    os.replace(temporary, path)


def plan(run):
    path = safe_run(run) / 'plan.json'
    if not path.is_file():
        raise ValueError('Missing registered plan: ' + str(path))
    data = read(path)
    tasks = data.get('tasks')
    if data.get('run_id') != run or not isinstance(tasks, list) or not tasks:
        raise ValueError('Malformed plan')
    seen = set()
    for task in tasks:
        ident = task.get('id')
        if not isinstance(ident, str) or not IDENT.fullmatch(ident) or ident in seen:
            raise ValueError('Duplicate/invalid task ID')
        seen.add(ident)
        if not isinstance(task.get('acceptance'), list) or not task['acceptance']:
            raise ValueError('Acceptance criteria required for ' + ident)
    for task in tasks:
        deps = task.get('depends_on', [])
        if not isinstance(deps, list) or len(deps) != len(set(deps)) or task['id'] in deps or any(x not in seen for x in deps):
            raise ValueError('Invalid dependencies for ' + task['id'])
    mapping = {t['id']: t.get('depends_on', []) for t in tasks}
    visited, active = set(), set()
    def visit(tid):
        if tid in active: raise ValueError('Dependency cycle')
        if tid in visited: return
        active.add(tid)
        for dep in mapping[tid]: visit(dep)
        active.remove(tid)
        visited.add(tid)
    for tid in mapping: visit(tid)
    return tasks


def state_path(run):
    return safe_run(run) / 'internal-auto.json'


def state(run):
    path = state_path(run)
    tasks = plan(run)
    if not path.exists():
        raise ValueError('No internal execution registered: run init')
    data = read(path)
    if data.get('schema') != 1 or data.get('run_id') != run:
        raise ValueError('Invalid state')
    if set(data.get('tasks', {})) != {t['id'] for t in tasks}:
        raise ValueError('Plan changed: reconcile before resume')
    for t in tasks:
        record = data['tasks'][t['id']]
        if record.get('depends_on') != t.get('depends_on', []) or record.get('acceptance') != t['acceptance']:
            raise ValueError('Plan changed: reconcile before resume')
    return data, tasks


def initialize(run):
    tasks = plan(run)
    path = state_path(run)
    if path.exists():
        return state(run)[0]
    data = {'schema': 1, 'run_id': run, 'created_at': stamp(), 'tasks': {t['id']: {
        'status': 'PLANNED', 'role': 'architect', 'depends_on': t.get('depends_on', []),
        'acceptance': t['acceptance'], 'evidence': {}, 'attempts': 0
    } for t in tasks}}
    write(path, data)
    return data


def ready(data, tasks):
    result = []
    for task in tasks:
        t = data['tasks'][task['id']]
        deps = t['depends_on']
        if t['status'] in ('COMPLETED', 'BLOCKED'):
            continue
        if all(data['tasks'][d]['status'] == 'COMPLETED' for d in deps):
            result.append({'task_id': task['id'], 'role': t['role'], 'status': t['status'], 'acceptance': t['acceptance']})
    return result


def next_task(run):
    data, tasks = state(run)
    tasks_ready = ready(data, tasks)
    if not tasks_ready:
        return {'run_id': run, 'ready': [], 'message': 'All tasks completed/blocked or waiting on dependencies'}
    return {'run_id': run, 'ready': tasks_ready[:1], 'instruction': 'The same host assistant performs the next role. No external AI is launched. Never claim work or tests without evidence.'}


def record(run, task_id, role, evidence, approved=False):
    data, tasks = state(run)
    if task_id not in data['tasks']: raise ValueError('Unknown task')
    task = data['tasks'][task_id]
    if task['status'] in ('COMPLETED', 'BLOCKED'): raise ValueError('Task already terminal')
    if task['role'] != role: raise ValueError('Out of order; expected ' + task['role'])
    if any(data['tasks'][dep]['status'] != 'COMPLETED' for dep in task['depends_on']):
        raise ValueError('Unfinished dependencies')
    if not evidence.strip() or len(evidence) > 50000:
        raise ValueError('Concrete evidence required (max 50000 chars)')
    task['evidence'][role] = {'details': evidence, 'timestamp': stamp()}
    if role == 'reviewer':
        if approved:
            if not all(x in task['evidence'] for x in ROLES):
                raise ValueError('Missing earlier role evidence')
            task['status'], task['role'] = 'COMPLETED', None
        else:
            task['status'], task['role'] = 'NEEDS_REVISION', 'developer'
            task['attempts'] += 1
            # Retesting and rereview mandatory after revisions.
            task['evidence'].pop('tester', None)
            task['evidence'].pop('reviewer', None)
    else:
        task['status'] = 'IN_PROGRESS'
        task['role'] = ROLES[ROLES.index(role) + 1]
    write(state_path(run), data)
    return {'task_id': task_id, 'status': task['status'], 'next_role': task['role']}


def block(run, task_id, reason):
    data, _ = state(run)
    if task_id not in data['tasks']: raise ValueError('Unknown task')
    if data['tasks'][task_id]['status'] == 'COMPLETED': raise ValueError('Cannot block completed task')
    if not reason.strip(): raise ValueError('Reason required')
    data['tasks'][task_id].update(status='BLOCKED', block_reason=reason)
    write(state_path(run), data)
    return {'blocked': task_id, 'reason': reason}


def markdown(run):
    data, tasks = state(run)
    lines = ['# Internal AI execution — ' + run, '', 'Generated from registered runtime state. Do not manually mark tasks DONE.', '', '| ID | Status | Next role | Dependencies |', '|---|---|---|---|']
    for t in tasks:
        s = data['tasks'][t['id']]
        lines.append('| {0} | {1} | {2} | {3} |'.format(t['id'], s['status'], s['role'] or '—', ', '.join(s['depends_on']) or '—'))
    lines += ['', '## Evidence']
    for t in tasks:
        lines += ['', '### ' + t['id']]
        for role, item in data['tasks'][t['id']]['evidence'].items():
            lines.append('- {0}: {1}'.format(role, item['details'].replace('\n', ' ')[:2000]))
    target = safe_run(run) / 'internal-auto-report.md'
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'report': str(target), 'tasks': {k: v['status'] for k, v in data['tasks'].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init'); sub.add_parser('next'); sub.add_parser('status'); sub.add_parser('report')
    rec = sub.add_parser('record'); rec.add_argument('task_id'); rec.add_argument('role', choices=ROLES)
    rec.add_argument('--evidence', required=True); rec.add_argument('--approve', action='store_true')
    blk = sub.add_parser('block'); blk.add_argument('task_id'); blk.add_argument('--reason', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init': output = initialize(args.run)
        elif args.command == 'next': output = next_task(args.run)
        elif args.command == 'status': output = state(args.run)[0]
        elif args.command == 'record': output = record(args.run, args.task_id, args.role, args.evidence, args.approve)
        elif args.command == 'block': output = block(args.run, args.task_id, args.reason)
        else: output = markdown(args.run)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, 'ERROR: ' + str(error) + '\n')

if __name__ == '__main__': main()
