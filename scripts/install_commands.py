#!/usr/bin/env python3
"""Install project-local native commands in target, without installing dependencies.
No external process, network call or model execution. Existing files are never overwritten
unless --overwrite; show the proposed changes with --dry-run.
"""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    'claude': '.claude/commands',
    'cursor': '.cursor/commands',
    'gemini': '.gemini/commands',
    'opencode': '.opencode/commands',
    'copilot': '.github/prompts',
    'codex': '.agents/skills',
}

def install(target: Path, platforms: list[str], dry_run=False, overwrite=False):
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f'Target must be an existing directory: {target}')
    copied=skipped=0
    for platform in platforms:
        folder=Path(PLATFORMS[platform]); src=ROOT/folder
        for file in sorted(src.rglob('*')):
            if not file.is_file(): continue
            relative=file.relative_to(ROOT)
            dest=target/relative
            if dest.exists() and not overwrite:
                print('SKIP existing:',dest);skipped+=1;continue
            if not dry_run:
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(file,dest)
            print('WOULD COPY' if dry_run else 'COPIED',file.relative_to(ROOT),'->',dest)
            copied+=1
    print(f'Files {"planned" if dry_run else "copied"}: {copied}; skipped: {skipped}')
    return copied,skipped

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--target',type=Path,required=True)
    ap.add_argument('--platforms',nargs='+',choices=[*PLATFORMS,'all'],default=['all'])
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--overwrite',action='store_true',help='Explicit permission to overwrite existing command files')
    args=ap.parse_args()
    chosen=list(PLATFORMS) if 'all' in args.platforms else list(dict.fromkeys(args.platforms))
    try:install(args.target,chosen,args.dry_run,args.overwrite)
    except (OSError,ValueError) as e:ap.error(str(e))
if __name__=='__main__':main()
