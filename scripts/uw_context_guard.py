#!/usr/bin/env python3
"""Context guard for Universal AI Workflow 6.9+ (drop-in, stdlib only).

WHY: splitting a plan into tasks does NOT split the model's context window.
When uw-auto runs in preview / in-host mode, every task, every role, every
report and every test log stays in ONE conversation. This tool gives the host
assistant a compact view of run state and a hard "stop and hand off" signal.

Commands:
  brief   -- compact JSON view of the run (never prints evidence/logs)
  prompt  -- write FRESH_PROMPT.md: paste it into a NEW chat to resume
  check   -- estimate context cost; exit 2 => stop, hand off, open new chat
  trim    -- preview/apply shortening of stored evidence (full copy preserved)

No network, no subprocess, no model calls, no git writes. Estimates are
UTF-8 bytes/4 and are NOT provider billing or real tokenizer counts.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
ROLES = ('architect', 'developer', 'tester', 'reviewer')
SCHEMA = 1

# Files a host commonly injects at session start. Only existing ones count.
FIXED_DOCS = (
    'AGENTS.md', 'AI_INSTRUCTIONS.md', 'CLAUDE.md', 'GEMINI.md',
    '.github/copilot-instructions.md', '.cursor/rules/universal-workflow.mdc',
    '.ai/HANDOFF.md', '.ai/STATE.md', '.ai/TASKS.md', '.ai/DECISIONS.md',
    '.ai/MANIFEST.md', '.ai/CONTEXT_POLICY.md',
)
SKIP_NAMES = {'FRESH_PROMPT.md'}
SKIP_SUFFIX = ('.full.json', '.bak')


def est(nbytes):
    return (nbytes + 3) // 4


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                     prefix='.ctx-', delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        tmp = handle.name
    os.replace(tmp, path)


def inside(root, rel):
    root = Path(root).resolve()
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Path escapes project root: ' + str(rel))
    return target


def run_dir(root, run):
    if not IDENT.fullmatch(run):
        raise ValueError('Invalid run ID')
    return inside(root, Path('.ai') / 'runs' / run)


def load_run(root, run):
    """Return (plan, state_or_None). Works with 6.9 internal-auto and 6.8 plan-only."""
    folder = run_dir(root, run)
    plan_path = folder / 'plan.json'
    if not plan_path.is_file():
        raise ValueError('Missing registered plan: ' + str(plan_path))
    plan = read_json(plan_path)
    if plan.get('run_id') != run or not isinstance(plan.get('tasks'), list):
        raise ValueError('Malformed plan')
    state_path = folder / 'internal-auto.json'
    state = read_json(state_path) if state_path.is_file() else None
    if state is not None and (state.get('schema') != SCHEMA or not isinstance(state.get('tasks'), dict)):
        raise ValueError('Malformed internal-auto state')
    return plan, state


def task_map(plan):
    return {t['id']: t for t in plan['tasks'] if isinstance(t, dict) and 'id' in t}


def ready_tasks(plan, state):
    by_id = task_map(plan)
    if state is None:
        return [{'task_id': t['id'], 'role': t.get('role', 'developer'),
                 'status': t.get('status', 'PLANNED')}
                for t in plan['tasks'] if t.get('status') in (None, 'PLANNED', 'ACTIVE')]
    statuses = {tid: rec.get('status') for tid, rec in state['tasks'].items()}
    out = []
    for task in plan['tasks']:
        tid, rec = task['id'], state['tasks'].get(task['id'], {})
        if rec.get('status') in ('COMPLETED', 'BLOCKED'):
            continue
        deps = rec.get('depends_on', task.get('depends_on', []))
        if all(statuses.get(dep) == 'COMPLETED' for dep in deps):
            out.append({'task_id': tid, 'role': rec.get('role') or 'architect',
                        'status': rec.get('status', 'PLANNED')})
    return out


def last_verification(state, limit=180):
    """Short, bounded snippet only. Never returns the whole evidence set."""
    if not state:
        return 'none'
    best = None
    for tid, rec in state['tasks'].items():
        for role, item in (rec.get('evidence') or {}).items():
            stamp = item.get('timestamp', '') if isinstance(item, dict) else ''
            if role in ('tester', 'reviewer') and (best is None or stamp > best[0]):
                best = (stamp, tid, role, str(item.get('details', '')) if isinstance(item, dict) else str(item))
    if not best:
        return 'none'
    text = ' '.join(best[3].split())
    return f'{best[1]}/{best[2]}: {text[:limit]}' + (' …' if len(text) > limit else '')


def brief(root, run):
    plan, state = load_run(root, run)
    by_id = task_map(plan)
    ready = ready_tasks(plan, state)
    counts = {}
    if state:
        for rec in state['tasks'].values():
            key = rec.get('status', 'UNKNOWN')
            counts[key] = counts.get(key, 0) + 1
    else:
        for task in plan['tasks']:
            key = task.get('status', 'PLANNED')
            counts[key] = counts.get(key, 0) + 1
    blocked = []
    if state:
        blocked = [{'task_id': tid, 'reason': ' '.join(str(rec.get('block_reason', '')).split())[:160]}
                   for tid, rec in state['tasks'].items() if rec.get('status') == 'BLOCKED']
    current = ready[0] if ready else None
    if current:
        task = by_id.get(current['task_id'], {})
        current['acceptance'] = list(task.get('acceptance', []))[:8]
        current['paths'] = list(task.get('paths', []))[:12]
        current['depends_on'] = list(task.get('depends_on', []))[:8]
        if state:
            current['next_command'] = (
                f'python scripts/uw_internal_auto.py --run {run} record '
                f'{current["task_id"]} {current["role"]} --evidence "SHORT SUMMARY + LOG PATH"'
                + (' --approve' if current['role'] == 'reviewer' else ''))
        else:
            current['next_command'] = (
                f'python scripts/auto_runner.py --run {run} --agent AGENT_NAME '
                f'--config examples/agents.example.json  # preview only')
    result = {
        'mode': 'internal-auto' if state else 'plan-only',
        'run_id': run,
        'counts': counts,
        'ready_count': len(ready),
        'current': current,
        'blocked': blocked[:5],
        'last_verification': last_verification(state),
        'context_rules': [
            'ONE task (or one 4-role cycle) per chat when no external CLI agent is launched.',
            'NEVER read internal-auto.json, internal-auto-report.md, auto/report.json or *.log in full.',
            'Redirect build/test output to a file; paste only summary + exit code + path.',
            'On check over_budget: stop, run prompt, open a NEW chat with FRESH_PROMPT.md.',
        ],
        'estimate_note': 'bytes/4 approximation; not provider usage',
    }
    result['estimated_tokens'] = est(len(json.dumps(result, ensure_ascii=False).encode('utf-8')))
    return result


def fresh_prompt(root, run, output=None):
    b = brief(root, run)
    cur = b['current']
    lines = [
        f'# استكمال مهمة واحدة — {run}',
        '',
        'أنت في محادثة جديدة. لا تطلب سجل المحادثة السابقة ولا تقرأ ملفات الحالة الكاملة.',
        'الهدف: تنفيذ مهمة واحدة فقط ثم التوقف وتسليم العمل لمحادثة جديدة.',
        '',
        '## اقرأ فقط',
        '- AGENTS.md و .ai/HANDOFF.md (وضع Lite)',
        f'- نفّذ: `python scripts/uw_context_guard.py --root . brief --run {run}`',
        f'- نفّذ: `python scripts/uw_context_guard.py --root . check --run {run} --max-tokens 12000`',
        '- افتح ملفات المصدر الخاصة بالمهمة فقط (1–10 ملفات كحد أقصى).',
        '',
        '## لا تقرأ أبدًا داخل المحادثة',
        '`internal-auto.json`, `internal-auto-report.md`, `auto/report.json`, `*.log`, ومخرجات الاختبارات الكاملة.',
        '',
        '## المهمة الحالية',
    ]
    if cur:
        lines += [
            f'- المعرّف: `{cur["task_id"]}` — الحالة: {cur["status"]} — الدور التالي: {cur["role"]}',
            f'- النطاق المملوك: {", ".join(cur.get("paths", [])) or "غير محدد في الخطة"}',
            '- شروط القبول:',
        ]
        lines += [f'  - {x}' for x in cur.get('acceptance', [])] or ['  - غير محدد']
        lines += [f'- الأمر بعد الإنجاز: `{cur["next_command"]}`']
    else:
        lines += ['- لا توجد مهمة جاهزة: راجع الاعتماديات أو المحظورات ثم أبلغ المستخدم.']
    lines += [
        '',
        '## الحالة المختصرة',
        f'- العدّادات: {json.dumps(b["counts"], ensure_ascii=False)}',
        f'- آخر تحقق: {b["last_verification"]}',
        f'- محظور: {json.dumps(b["blocked"], ensure_ascii=False)}',
        '',
        '## قواعد إلزامية',
        '1. وجّه مخرجات البناء/الاختبار إلى ملف (`*> test.log`) واذكر فقط: الأمر + exit code + عدد الاختبارات + آخر 5 أسطر.',
        '2. الدليل (evidence) ≤ 200 كلمة ويحتوي على مسار السجل بدلًا من محتواه.',
        '3. عند ظهور `over_budget=true` أو بعد إغلاق مهمة: توقف فورًا، شغّل `prompt`، واطلب من المستخدم فتح محادثة جديدة.',
        '4. لا تدّعِ تنفيذ وكلاء خارجيين أو اختبارات لم تُرَ مخرجاتها فعلًا.',
        '5. لا commit / merge / push / deploy دون موافقة صريحة.',
        '',
        '## ملاحظة تصميمية',
        'تقسيم المهام هنا هو تقسيم ملكية ملفات، وليس تقسيم نافذة السياق. العزل الحقيقي يكون إما بمحادثة جديدة لكل مهمة،',
        'أو بتشغيل CLI خارجي مستقل لكل مهمة عبر `--approve-agents --approve-worktrees` (تكلفة منفصلة على المزود).',
    ]
    text = '\n'.join(lines) + '\n'
    dest = inside(root, output) if output else run_dir(root, run) / 'FRESH_PROMPT.md'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding='utf-8')
    words = len(text.split())
    if words > 450:
        raise ValueError(f'Fresh prompt too long ({words} words); shorten evidence')
    return {'prompt': str(dest.relative_to(Path(root).resolve())), 'words': words,
            'estimated_tokens': est(len(text.encode('utf-8'))), 'over_budget_hint':
            'Paste this file into a NEW chat; do not paste prior conversation history.'}


def context_files(root, run):
    root = Path(root).resolve()
    files = []
    for rel in FIXED_DOCS:
        p = root / rel
        if p.is_file():
            files.append((rel, p))
    # Installed command/skill definitions are fixed per-turn overhead in some hosts.
    for p in sorted((root / '.agents' / 'skills').glob('*/SKILL.md')):
        files.append((str(p.relative_to(root)), p))
    if (root / 'commands' / 'registry.json').is_file():
        files.append(('commands/registry.json', root / 'commands' / 'registry.json'))
    folder = run_dir(root, run)
    if folder.is_dir():
        for p in sorted(folder.rglob('*')):
            if not p.is_file() or p.name in SKIP_NAMES or p.name.endswith(SKIP_SUFFIX):
                continue
            files.append((str(p.relative_to(root)), p))
    reports = root / '.ai' / 'reports'
    if reports.is_dir():
        for p in sorted(reports.glob('*')):
            if p.is_file():
                files.append((str(p.relative_to(root)), p))
    seen, unique = set(), []
    for rel, p in files:
        if rel not in seen:
            seen.add(rel)
            unique.append((rel, p))
    return unique


def check(root, run, max_tokens=12000):
    rows = []
    for rel, p in context_files(root, run):
        n = p.stat().st_size
        rows.append({'file': rel, 'bytes': n, 'estimated_tokens': est(n)})
    rows.sort(key=lambda x: -x['estimated_tokens'])
    total = sum(r['estimated_tokens'] for r in rows)
    over = total > max_tokens
    result = {
        'run_id': run, 'max_tokens': max_tokens, 'total_estimate': total,
        'over_budget': over, 'files_counted': len(rows), 'top': rows[:10],
        'recommendation': (
            'STOP: run `prompt`, hand FRESH_PROMPT.md to a NEW chat, or launch external CLI agents.'
            if over else 'Within budget estimate; still avoid reading full state/logs.'),
        'disclaimer': 'UTF-8 bytes/4 estimate of FILE SIZES, not live provider context or billing.',
    }
    return result


def trim(root, run, max_chars=800, apply=False):
    folder = run_dir(root, run)
    path = folder / 'internal-auto.json'
    if not path.is_file():
        raise ValueError('No internal-auto.json; nothing to trim (plan-only run)')
    data = read_json(path)
    backup = folder / 'internal-auto.full.json'
    changes, saved = [], 0
    for tid, rec in data.get('tasks', {}).items():
        for role, item in (rec.get('evidence') or {}).items():
            if not isinstance(item, dict) or 'details' not in item:
                continue
            text = str(item['details'])
            if len(text) > max_chars:
                saved += len(text) - max_chars - 60
                changes.append({'task_id': tid, 'role': role,
                                'from': len(text), 'to': max_chars + 60})
                item['details'] = text[:max_chars].rstrip() + f' …[full: internal-auto.full.json#{tid}/{role}]'
                item['trimmed'] = True
    out = {'run_id': run, 'apply': bool(apply), 'max_chars': max_chars,
           'changes': changes, 'chars_saved_estimate': max(saved, 0),
           'backup': str(backup.relative_to(Path(root).resolve())),
           'note': 'Preview only unless --apply. Full evidence is preserved in the backup.'}
    if apply and changes:
        if not backup.exists():
            atomic_json(backup, read_json(path))
        atomic_json(path, data)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.', help='project root (default: current directory)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('brief'); p.add_argument('--run', required=True)
    p = sub.add_parser('prompt'); p.add_argument('--run', required=True); p.add_argument('--output')
    p = sub.add_parser('check'); p.add_argument('--run', required=True)
    p.add_argument('--max-tokens', type=int, default=12000)
    p = sub.add_parser('trim'); p.add_argument('--run', required=True)
    p.add_argument('--max-chars', type=int, default=800); p.add_argument('--apply', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'check' and a.max_tokens < 1:
        ap.error('--max-tokens must be positive')
    if a.cmd == 'trim' and not 100 <= a.max_chars <= 50000:
        ap.error('--max-chars must be 100..50000')
    try:
        if a.cmd == 'brief':
            result, code = brief(a.root, a.run), 0
        elif a.cmd == 'prompt':
            result, code = fresh_prompt(a.root, a.run, a.output), 0
        elif a.cmd == 'check':
            result = check(a.root, a.run, a.max_tokens)
            code = 2 if result['over_budget'] else 0
        else:
            result, code = trim(a.root, a.run, a.max_chars, a.apply), 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
