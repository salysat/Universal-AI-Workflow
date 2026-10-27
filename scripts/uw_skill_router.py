#!/usr/bin/env python3
"""Local-only skill routing for uw-autopilot.

NO network calls, NO installs, NO execution. Built-in `uw-*` commands are
repo-owned instruction files and may be *read* by an agent. Third-party skills
are included only when they are already vendored locally, pinned by SHA-256,
reviewed, unexpired and explicitly approved in the registry or in the
autopilot config. "Loading a skill" here means telling the agent which reviewed
local file to read -- never copying the whole skill into the host context.
"""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

BUILTIN_TRIGGERS = {
    'uw-context': ['context', 'token', 'budget', 'handoff', 'resume', 'session', 'سياق', 'توكن', 'تسليم'],
    'uw-build': ['implement', 'code', 'fix', 'feature', 'change', 'edit', 'migration', 'إصلاح', 'تطوير', 'كود', 'تحويل'],
    'uw-test': ['test', 'verify', 'validate', 'build', 'exit', 'check', 'اختبار', 'فحص', 'تحقق'],
    'uw-review': ['review', 'diff', 'quality', 'risk', 'مراجعة'],
    'uw-security': ['security', 'auth', 'secret', 'permission', 'injection', 'أمان', 'صلاحية'],
    'uw-plan': ['plan', 'scope', 'dependency', 'partition', 'خطة', 'تقسيم'],
    'uw-recon': ['inspect', 'explore', 'discover', 'structure', 'استكشاف'],
    'uw-handoff': ['handoff', 'transfer', 'resume'],
    'uw-audit': ['audit', 'sarif', 'finding', 'scan'],
    'uw-init': ['init', 'setup', 'state', 'تهيئة'],
    'uw-status': ['status', 'progress', 'حالة'],
    'uw-agents': ['agent', 'parallel', 'worktree', 'وكيل'],
    'uw-auto': ['orchestr', 'auto', 'migration'],
    'uw-team': ['role', 'architect', 'developer', 'tester', 'reviewer'],
    'uw-ship': ['deploy', 'release', 'publish', 'نشر'],
    'uw-v6': ['llm', 'planner', 'repair'],
    'uw-help': ['help', 'explain'],
}

PLATFORM_PATHS = (
    '.agents/skills/{name}/SKILL.md',
    '.claude/commands/{name}.md',
    '.cursor/commands/{name}.md',
    '.opencode/commands/{name}.md',
    '.gemini/commands/{name}.toml',
    '.github/prompts/{name}.prompt.md',
)


def within(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise ValueError('Path escapes project root: ' + str(rel))
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def score(text, triggers, extra_words=()):
    """Conservative keyword score. Latin words use boundaries; Arabic uses substring."""
    text = (text or '').casefold()
    words = set(re.findall(r'[a-z0-9_-]+', text))
    hits = 0
    for trigger in triggers:
        t = trigger.casefold()
        if re.fullmatch(r'[a-z0-9_-]+', t):
            if t in words:
                hits += 2
        elif t in text:
            hits += 2
    for word in extra_words:
        w = str(word).casefold()
        if re.fullmatch(r'[a-z0-9_-]+', w) and len(w) > 3 and w in words:
            hits += 1
    return hits


def builtin_path(root, name):
    for template in PLATFORM_PATHS:
        rel = template.format(name=name)
        p = root / rel
        if p.is_file():
            return rel
    return None


def approved_vendored(root, registry_rel='.ai/skills/REGISTRY.json'):
    """Third-party skills that pass every local trust check."""
    path = root / registry_rel
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError):
        return []
    today = dt.date.today().isoformat()
    out = []
    for item in data.get('skills', []):
        if not isinstance(item, dict):
            continue
        if not item.get('approved_for_execution') or item.get('review_status') != 'approved':
            continue
        if str(item.get('review_expires', '')) < today:
            continue
        rel = item.get('path')
        expected = item.get('sha256')
        if not isinstance(rel, str) or not isinstance(expected, str):
            continue
        try:
            p = within(root, rel)
            if not p.is_file() or sha256(p).lower() != expected.lower():
                continue
        except (ValueError, OSError):
            continue
        out.append({'id': item.get('id'), 'path': rel, 'triggers': item.get('triggers', []),
                    'kind': 'vendored', 'trust': 'pinned-sha256-reviewed'})
    return out


def approved_extra(root, extra_skills):
    """Operator-declared local skills; hash must be supplied and match."""
    out = []
    for item in extra_skills or []:
        if not isinstance(item, dict) or not item.get('approved'):
            continue
        rel, expected = item.get('path'), item.get('sha256')
        if not isinstance(rel, str) or not isinstance(expected, str) or len(expected) != 64:
            continue
        try:
            p = within(root, rel)
            if not p.is_file() or sha256(p).lower() != expected.lower():
                continue
        except (ValueError, OSError):
            continue
        out.append({'id': item.get('id') or Path(rel).name, 'path': rel,
                    'triggers': item.get('triggers', []), 'kind': 'local-approved',
                    'trust': 'config-pinned-sha256'})
    return out


def route(root, task, registry=None, extra_skills=None, max_skills=3):
    """Return compact, ranked, LOCAL skill references for one task."""
    root = Path(root).resolve()
    text = ' '.join([str(task.get('id', '')), str(task.get('description', '')),
                     ' '.join(str(x) for x in task.get('acceptance', [])),
                     ' '.join(str(x) for x in task.get('paths', []))])
    descriptions = {}
    if registry is None:
        reg_path = root / 'commands' / 'registry.json'
        if reg_path.is_file():
            try:
                registry = json.loads(reg_path.read_text(encoding='utf-8')).get('commands', {})
            except (OSError, json.JSONDecodeError):
                registry = {}
    else:
        registry = registry.get('commands', registry) if isinstance(registry, dict) else {}
    for name, value in (registry or {}).items():
        if isinstance(value, dict):
            descriptions[name] = str(value.get('description', ''))
    candidates = []
    for name, triggers in BUILTIN_TRIGGERS.items():
        rel = builtin_path(root, name)
        if not rel:
            continue
        s = score(text, triggers, [name.replace('uw-', ''), descriptions.get(name, '')])
        if s:
            candidates.append({'id': name, 'path': rel, 'kind': 'builtin',
                               'trust': 'repo-owned', 'score': s,
                               'reason': 'keyword match on built-in command'})
    for item in approved_vendored(root) + approved_extra(root, extra_skills):
        s = score(text, item.get('triggers', []), [item.get('id', '')])
        if s:
            candidates.append({**item, 'score': s, 'reason': 'reviewed local skill, hash verified'})
    candidates.sort(key=lambda x: (-x['score'], x['id']))
    selected, seen = [], set()
    for item in candidates:
        if item['id'] in seen:
            continue
        seen.add(item['id'])
        selected.append({k: item[k] for k in ('id', 'path', 'kind', 'trust', 'reason')})
        if len(selected) >= max(1, min(max_skills, 6)):
            break
    return {'skills': selected, 'network_used': False, 'auto_install': False,
            'note': 'Agent should READ these local files. No download, install or execution.'}


def prompt_block(routing):
    if not routing.get('skills'):
        return 'No extra skills routed. Use AGENTS.md only.'
    lines = ['Read these reviewed LOCAL skill/instruction files before starting (do not download or install anything):']
    lines += [f'- {s["path"]}  ({s["trust"]})' for s in routing['skills']]
    return '\n'.join(lines)
