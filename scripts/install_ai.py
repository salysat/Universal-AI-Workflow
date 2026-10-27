#!/usr/bin/env python3
"""Install Universal AI Workflow into an existing local project.

Works with an already extracted source tree, or clones an authenticated Git repository
into a temporary folder using the user's existing git credential manager/SSH agent.
No network access or execution of repository code is performed for local installs.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from install_commands import ROOT, PLATFORMS, install

RUNTIME_FILES = ['AGENTS.md', 'AI_INSTRUCTIONS.md', 'scripts/workflow.py', 'scripts/agent_runner.py', 'scripts/auto_runner.py', 'scripts/ai_discovery.py', 'scripts/auto_plan.py', 'scripts/v5_auto.py', 'scripts/uw_v6.py', 'scripts/uw_dashboard.py', 'scripts/uw_audit.py', 'scripts/uw_efficiency.py', 'scripts/uw_internal_team.py', 'scripts/uw_internal_auto.py', 'scripts/uw_context_guard.py', 'scripts/uw_autopilot.py', 'scripts/uw_skill_router.py', 'scripts/uw_file_edit.py', 'scripts/generate_commands.py', 'commands/registry.json',
                 '.ai/schema.json', '.ai/CONTEXT_POLICY.md', '.ai/HANDOFF_TEMPLATE.md',
                 '.ai/skills/REGISTRY.json', '.ai/skills/ROUTER.md', '.ai/skills/REVIEW_CHECKLIST.md']
RUNTIME_INITIAL = ['.ai/STATE.md', '.ai/TASKS.md', '.ai/DECISIONS.md', '.ai/HANDOFF.md', '.ai/MANIFEST.md']

def deploy(source: Path, target: Path, platforms: list[str], *, dry_run=False, overwrite=False):
    source, target = source.resolve(), target.resolve()
    if not target.is_dir(): raise ValueError(f'Target must be an existing directory: {target}')
    if not (source/'scripts/workflow.py').is_file(): raise ValueError('Not a Universal AI Workflow source directory')
    # Safety: never copy from target to itself, and do not install in a directory nested under source.
    if source == target or source in target.parents: raise ValueError('Choose an independent target project directory')
    for rel in RUNTIME_FILES + RUNTIME_INITIAL:
        src, dest = source/rel, target/rel
        if not src.is_file(): raise ValueError(f'Missing required source file: {rel}')
        # Never clobber existing project memory or agent policy, even with --overwrite.
        protected = rel in RUNTIME_INITIAL or rel == 'AGENTS.md'
        if dest.exists() and (protected or not overwrite):
            print('SKIP existing:', dest); continue
        print('WOULD COPY' if dry_run else 'COPIED', rel)
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    # Keep transient orchestration state out of Git without rewriting project rules.
    ignore=target/'.gitignore'
    if not dry_run:
        existing=ignore.read_text(encoding='utf-8') if ignore.exists() else ''
        additions=[line for line in ('.ai/runs/','.ai/usage.jsonl','.ai/resume-snapshot.json','__pycache__/') if line not in existing.splitlines()]
        if additions:
            with ignore.open('a',encoding='utf-8') as handle:
                handle.write(('\n' if existing and not existing.endswith('\n') else '')+'\n'.join(additions)+'\n')
    # Install command definitions from the selected source, not from the installer's checkout.
    import install_commands
    original = install_commands.ROOT
    try:
        install_commands.ROOT = source
        return install_commands.install(target, platforms, dry_run=dry_run, overwrite=overwrite)
    finally:
        install_commands.ROOT = original

def vetted_repo(repo):
    p = urlparse(repo)
    if p.scheme == 'https' and p.hostname == 'github.com' and not p.username and not p.password and p.path.endswith('.git'):
        return repo
    if p.scheme == 'https' and p.hostname == 'github.com' and not p.username and not p.password and p.path.count('/') >= 2:
        return repo
    if repo.startswith('git@github.com:') and repo.endswith('.git'):
        return repo
    raise ValueError('Only GitHub HTTPS URLs without inline credentials, or GitHub SSH URLs, are accepted')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group()
    source.add_argument('--source', type=Path, help='Local extracted Universal AI Workflow directory')
    source.add_argument('--repo', help='GitHub repo URL (private repository needs existing Git authentication)')
    ap.add_argument('--ref', help='Git branch/tag (repo mode only)')
    ap.add_argument('--target', type=Path, required=True)
    ap.add_argument('--platforms', nargs='+', choices=[*PLATFORMS, 'all'], default=['all'])
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true', help='Replace non-protected existing integration files')
    args = ap.parse_args()
    platforms = list(PLATFORMS) if 'all' in args.platforms else list(dict.fromkeys(args.platforms))
    try:
        if args.ref and not args.repo: raise ValueError('--ref requires --repo')
        if args.repo:
            repo = vetted_repo(args.repo)
            if args.dry_run:
                print('Repo dry-run cannot preview remote files; use --source for a no-network preview')
                return
            with tempfile.TemporaryDirectory(prefix='uw-installer-') as td:
                checkout = Path(td)/'source'
                cmd = ['git', 'clone', '--depth', '1']
                if args.ref: cmd += ['--branch', args.ref]
                cmd += [repo, str(checkout)]
                subprocess.run(cmd, check=True)
                deploy(checkout, args.target, platforms, overwrite=args.overwrite)
        else:
            deploy(args.source or ROOT, args.target, platforms, dry_run=args.dry_run, overwrite=args.overwrite)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        ap.error(str(e))
if __name__ == '__main__': main()
