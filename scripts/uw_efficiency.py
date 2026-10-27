#!/usr/bin/env python3
"""Portable, read-only workflow efficiency diagnostics; stdlib only. Ledger append requires explicit command.
No provider network calls, shell execution, or automatic installs.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.ai'
DEFAULT_CONTEXT=12000
MAX_FILE=2_000_000

def within(root, raw):
    root=Path(root).resolve()
    p=(root/raw).resolve()
    if not p.is_relative_to(root): raise ValueError('Path escapes workspace')
    if not p.is_file(): raise ValueError('File not found: '+str(raw))
    if p.stat().st_size>MAX_FILE: raise ValueError('File exceeds safe inspection limit')
    return p

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(65536),b''): h.update(block)
    return h.hexdigest()

def estimate(b):
    # Approximation only: provider-specific tokenization varies significantly.
    return (len(b)+3)//4

def budget(files,root=ROOT,max_tokens=DEFAULT_CONTEXT):
    if max_tokens<1: raise ValueError('budget must be positive')
    remaining=max_tokens; data=[]
    for name in files:
        p=within(root,name)
        n=estimate(p.read_bytes()); accepted=n<=remaining
        data.append(dict(file=name,estimated_tokens=n,included=accepted))
        if accepted: remaining-=n
    return dict(budget_estimate=max_tokens,remaining_estimate=remaining,files=data,disclaimer='UTF-8 bytes/4 approximation; not billing or actual context usage')

def snapshot(files,root=ROOT):
    return dict(schema_version=1,created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),files={str(name):digest(within(root,name)) for name in files})

def verify(snap,root=ROOT):
    if snap.get('schema_version')!=1 or not isinstance(snap.get('files'),dict):raise ValueError('Invalid snapshot')
    results={}
    for name,expected in snap['files'].items():
        try: results[name]='MATCH' if digest(within(root,name))==expected else 'CHANGED'
        except (ValueError,OSError):results[name]='MISSING_OR_UNSAFE'
    return dict(ok=all(v=='MATCH' for v in results.values()),results=results)

def detect_type(path):
    with open(path,'rb') as f: b=f.read(64)
    if b.startswith(b'%PDF-'): return 'pdf'
    if b.startswith(b'PK\x03\x04'): return 'zip-container (may be docx/xlsx/pptx)'
    if b.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
    if b.startswith(b'\xff\xd8\xff'):return 'jpeg'
    if b.startswith(b'GIF8'):return 'gif'
    if b.startswith(b'SQLite format 3\x00'):return 'sqlite'
    if b.startswith(b'\x7fELF'):return 'executable-elf'
    if b.startswith(b'MZ'):return 'executable-pe'
    if b'\x00' in b:return 'binary-unknown'
    try: path.read_text(encoding='utf-8');return 'text-utf8'
    except UnicodeDecodeError:return 'binary-or-other-encoding'

def provider_health(config=None):
    names={'codex':'codex','claude':'claude','gemini':'gemini','cursor':'cursor','opencode':'opencode'}
    if config:
        data=json.loads(Path(config).read_text(encoding='utf-8'))
        names=data.get('providers',names)
        if not isinstance(names,dict) or not all(isinstance(x,str) for x in names.values()):raise ValueError('Invalid providers mapping')
    return {key:dict(installed=bool(shutil.which(binary)),executable=shutil.which(binary),authenticated='NOT_CHECKED',api_available='NOT_CHECKED') for key,binary in names.items()}

def skill_route(query,registry=STATE/'skills/REGISTRY.json'):
    data=json.loads(Path(registry).read_text(encoding='utf-8'))
    found=[]; q=query.casefold()
    for skill in data.get('skills',[]):
        triggers=skill.get('triggers',[])
        words=[v.casefold() for v in triggers if isinstance(v,str)]
        # Conservative routing: word overlap is a suggestion only, never execution.
        score=max([len(set(q.split()) & set(v.replace('/',' ').split())) for v in words] or [0])
        if score:
            found.append(dict(id=skill.get('id'),score=score,review_status=skill.get('review_status'),approved_for_execution=bool(skill.get('approved_for_execution')),action='SUGGEST_ONLY'))
    return sorted(found,key=lambda s:-s['score'])

def handoff_check(root=ROOT):
    req=['.ai/HANDOFF.md','.ai/STATE.md','.ai/TASKS.md','.ai/DECISIONS.md','.ai/MANIFEST.md']
    missing=[x for x in req if not (Path(root)/x).is_file()]
    content=(Path(root)/'.ai/HANDOFF.md').read_text(encoding='utf-8') if not missing else ''
    placeholders=[p for p in ('NOT SET','None confirmed','State not initialized') if p in content]
    return dict(ok=not missing and not placeholders,missing=missing,uninitialized_markers=placeholders,comment='Validation only; does not modify handoff')

def add_usage(path,provider,input_tokens,output_tokens,task):
    if any(n<0 for n in (input_tokens,output_tokens)):raise ValueError('Tokens cannot be negative')
    if not provider or not task:raise ValueError('Provider and task required')
    # Explicit external report only; never infer usage from estimate.
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    event=dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),provider=provider,task=task,input_tokens=input_tokens,output_tokens=output_tokens,source='user_supplied')
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    return event

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('budget');a.add_argument('files',nargs='+');a.add_argument('--max-tokens',type=int,default=DEFAULT_CONTEXT)
    a=sub.add_parser('snapshot');a.add_argument('files',nargs='+');a.add_argument('--output',required=True)
    a=sub.add_parser('resume-check');a.add_argument('--snapshot',required=True)
    a=sub.add_parser('inspect');a.add_argument('files',nargs='+')
    a=sub.add_parser('providers');a.add_argument('--config')
    a=sub.add_parser('skills');a.add_argument('query')
    sub.add_parser('handoff-check')
    a=sub.add_parser('usage-add');a.add_argument('--provider',required=True);a.add_argument('--task',required=True);a.add_argument('--input-tokens',type=int,required=True);a.add_argument('--output-tokens',type=int,required=True);a.add_argument('--output',default='.ai/usage.jsonl')
    a=p.parse_args()
    try:
        if a.cmd=='budget': result=budget(a.files,max_tokens=a.max_tokens)
        elif a.cmd=='snapshot':
            result=snapshot(a.files); dest=Path(a.output).resolve()
            if not dest.is_relative_to(ROOT.resolve()):raise ValueError('Snapshot output must be in project')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        elif a.cmd=='resume-check':result=verify(json.loads(within(ROOT,a.snapshot).read_text(encoding='utf-8')))
        elif a.cmd=='inspect':result={x:dict(type=detect_type(within(ROOT,x)),size=within(ROOT,x).stat().st_size) for x in a.files}
        elif a.cmd=='providers':result=provider_health(a.config)
        elif a.cmd=='skills':result=skill_route(a.query)
        elif a.cmd=='handoff-check':result=handoff_check()
        else:
            out=Path(a.output).resolve()
            if not out.is_relative_to((ROOT/'.ai').resolve()):raise ValueError('Usage log must be inside .ai')
            result=add_usage(out,a.provider,a.input_tokens,a.output_tokens,a.task)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if a.cmd in ('resume-check','handoff-check') and not result['ok']:return 2
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print('ERROR: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
