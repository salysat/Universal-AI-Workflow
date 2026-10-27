#!/usr/bin/env python3
"""Universal AI Workflow local controller; stdlib only."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / '.ai' / 'runs'
IDENT = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')

def die(message):
    raise ValueError(message)

def safe_ident(s):
    if not IDENT.fullmatch(s): die('Invalid ID (alphanumeric, underscores, hyphens only): ' + s)
    return s

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def save_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.tmp-', delete=False) as tmp:
        json.dump(data,tmp,indent=2,ensure_ascii=False); tmp.write('\n'); name=tmp.name
    os.replace(name,path)

def git(*args, cwd=ROOT, check=True):
    result = subprocess.run(['git',*args],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if check and result.returncode: die('git ' + ' '.join(args) + ': ' + result.stderr.strip())
    return result.stdout.strip()

def owner_path(raw):
    if not isinstance(raw,str) or not raw or '\\' in raw or raw.startswith('/') or ':' in raw:
        die('Unsafe owned path: '+repr(raw))
    parts = raw.rstrip('/').split('/')
    if any(p in ('','.','..') for p in parts): die('Unsafe owned path: '+repr(raw))
    return '/'.join(parts)

def collision(a,b):
    return a==b or a.startswith(b+'/') or b.startswith(a+'/')

def validate_plan(data):
    safe_ident(data['run_id'])
    tasks=data.get('tasks')
    if not isinstance(tasks,list) or not tasks: die('At least one task required')
    seen={}; owners=[]
    for task in tasks:
        tid=safe_ident(task['id'])
        if tid in seen: die('Duplicate task: '+tid)
        seen[tid]=True
        paths=task.get('paths',[])
        if not isinstance(paths,list) or not paths: die('Task must own at least one path: '+tid)
        if not isinstance(task.get('acceptance'),list) or not task['acceptance']: die('Acceptance criteria required for '+tid)
        for raw in paths:
            path=owner_path(raw)
            for other, who in owners:
                if collision(path,other): die(f'Ownership collision {tid}:{path} with {who}:{other}')
            owners.append((path,tid))
    return data

def file_for(run): return RUNS / safe_ident(run) / 'plan.json'

def load(run): return validate_plan(read_json(file_for(run)))

def validate():
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    if version!='6.11.0': die('Application VERSION mismatch')
    schema=read_json(ROOT/'.ai/schema.json')
    if schema.get('version')!='4.0': die('Protocol version mismatch')
    reg=read_json(ROOT/'.ai/skills/REGISTRY.json')
    if reg.get('schema_version')!='4.0': die('Registry version mismatch')
    essential=['AGENTS.md','AI_INSTRUCTIONS.md','.ai/HANDOFF.md','.ai/STATE.md','.ai/TASKS.md','.ai/CONTEXT_POLICY.md','README.md','SECURITY.md']
    for name in essential:
        if not (ROOT/name).is_file(): die('Missing: '+name)
    for item in reg.get('skills',[]):
        target=ROOT/owner_path(item['path'])
        if not target.is_file(): die('Missing skill: '+str(target))
        checksum=hashlib.sha256(target.read_bytes()).hexdigest()
        if checksum.lower()!=item['sha256'].lower(): die('Skill hash mismatch: '+item['id'])
        if item.get('approved_for_execution') and item.get('review_status')!='approved': die('Unreviewed approved skill: '+item['id'])
    limits=schema['limits']
    for fn,key in [('.ai/HANDOFF.md','handoff_words'),('.ai/STATE.md','state_words')]:
        words=len((ROOT/fn).read_text(encoding='utf-8-sig').split())
        if words>limits[key]: die(f'{fn} has {words} words, limit {limits[key]}')
    print('PASS: required files, protocol versions, skill hashes, and context limits')

def init(project):
    handoff=ROOT/'.ai/HANDOFF.md'
    if 'Universal AI Workflow V4' not in handoff.read_text(encoding='utf-8-sig') and handoff.stat().st_size:
        print('Existing HANDOFF preserved; edit for your project')
    (ROOT/'.ai/runs').mkdir(parents=True,exist_ok=True)
    print('Initialized runtime directories for',project)

def plan(f):
    data=validate_plan(read_json(f)); target=file_for(data['run_id'])
    if target.exists(): die('Run exists: '+data['run_id'])
    data['created_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    for t in data['tasks']: t['status']='PLANNED'
    save_json(target,data)
    print('Created',target.relative_to(ROOT))

def status(run=None):
    files=[file_for(run)] if run else sorted(RUNS.glob('*/plan.json'))
    if not files: print('No runs'); return
    for path in files:
        if not path.exists(): die('Run not found: '+str(path))
        data=read_json(path)
        print(data['run_id'],':',', '.join(t['id']+'='+t['status'] for t in data['tasks']))

def task_get(data, id):
    safe_ident(id)
    return next((x for x in data['tasks'] if x['id']==id),None) or die('Task not found: '+id)

def worktree(run, task):
    data=load(run); t=task_get(data,task)
    if t['status']!='PLANNED': die('Task must be PLANNED')
    top=Path(git('rev-parse','--show-toplevel')).resolve()
    if top!=ROOT.resolve(): die('Run command from repository root Git checkout')
    base=git('rev-parse','HEAD')
    branch='ai/'+run+'/'+task
    directory=ROOT.parent/(ROOT.name+'-agent-worktrees')/(run+'-'+task)
    if directory.exists(): die('Worktree location already exists')
    directory.parent.mkdir(parents=True,exist_ok=True)
    # Dependent tasks must see completed dependency commits before they start.
    dependencies=t.get('depends_on',[])
    for dep in dependencies:
        d=task_get(data,dep)
        if d['status'] not in ('DONE','MERGED') or not d.get('head'):
            die('Dependency must be DONE before worktree creation: '+dep)
    git('worktree','add','-b',branch,str(directory),base)
    try:
        for dep in dependencies:
            # --no-commit avoids silently creating a merge commit; the operator must
            # resolve any conflict and commit dependency integration explicitly.
            d=task_get(data,dep)
            merged=subprocess.run(['git','merge','--no-ff','--no-edit',d['head']],cwd=directory,capture_output=True,text=True)
            if merged.returncode: die('Dependency merge failed: '+dep+'; resolve or remove worktree manually: '+merged.stderr)
        base=git('rev-parse','HEAD',cwd=directory)
    except Exception:
        raise
    t.update(status='ACTIVE',branch=branch,worktree=str(directory),base=base)
    save_json(file_for(run),data)
    print('WORKTREE:',directory,'\nBRANCH:',branch,'\nOWNED:',', '.join(t['paths']))

def changed_files(worktree, base, head):
    result = subprocess.run(['git','diff','--name-only','-z',base,head],cwd=worktree,capture_output=True,check=False)
    if result.returncode: die('Cannot inspect committed changes: '+result.stderr.decode(errors='replace'))
    return [x.decode('utf-8','replace') for x in result.stdout.split(b'\0') if x]

def task_owns(path, owned):
    return any(path==p.rstrip('/') or path.startswith(p.rstrip('/')+'/') for p in owned)

def task_hash(task):
    return hashlib.sha256(json.dumps({k:task.get(k) for k in ('id','description','paths','acceptance','depends_on')},sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()

def complete(run,task,evidence):
    data=load(run); t=task_get(data,task)
    if t['status']!='ACTIVE': die('Task must be ACTIVE')
    w=Path(t['worktree']).resolve()
    if not w.is_dir(): die('Worktree not found')
    if git('status','--porcelain',cwd=w): die('Worktree must be committed or clean; no auto commits')
    if git('branch','--show-current',cwd=w)!=t['branch']: die('Unexpected worktree branch')
    head=git('rev-parse','HEAD',cwd=w)
    changed=changed_files(w,t['base'],head)
    if not changed: die('No committed changes; refusing empty completion')
    if any(not task_owns(f,t['paths']) for f in changed): die('Changes outside task ownership: '+repr([f for f in changed if not task_owns(f,t['paths'])]))
    gate_record=file_for(run).parent/('gate-'+task+'.json')
    if not gate_record.is_file(): die('Acceptance gate has not passed')
    g=read_json(gate_record)
    if g.get('head')!=head or g.get('task')!=task or not g.get('passed') or g.get('task_hash')!=task_hash(t):
        die('Acceptance gate is missing, failed, stale, or belongs to another task')
    if not isinstance(evidence,str) or len(evidence.strip())<10: die('Meaningful evidence required (10+ chars)')
    t.update(status='DONE',head=head,evidence=evidence,changed_files=changed,gate_results=g['results'],completed_at=dt.datetime.now(dt.timezone.utc).isoformat())
    save_json(file_for(run),data)
    print('DONE (tests PASS, human review still required):',task,'at',head)

# An operator-reviewed fixed allowlist, not arbitrary JSON executables.
# Additional commands require a reviewed code change to this mapping.
SAFE_COMMANDS = {
    'python-version': ['python','--version'],
    'python3-version': ['python3','--version'],
    'dotnet-version': ['dotnet','--version'],
    'dotnet-build': ['dotnet','build','--no-restore'],
    'dotnet-test': ['dotnet','test','--no-restore'],
    'python-unittest': [sys.executable,'-m','unittest','discover','-s','tests'],
    'npm-test': ['npm','test','--','--runInBand'],
    'npm-run-build': ['npm','run','build'],
    'pnpm-test': ['pnpm','test'],
    'go-test': ['go','test','./...'],
    'cargo-test': ['cargo','test','--locked'],
    'maven-test': ['mvn','test','--batch-mode'],
    'gradle-test': ['gradle','test','--no-daemon'],
    'pytest': [sys.executable,'-m','pytest'],
}

def resolve_gate_commands(commands, policy=None, policy_sha256=None):
    """A reviewed project policy requires an exact digest supplied outside the policy file."""
    if policy is None:
        if policy_sha256: die('Policy digest provided without a policy')
        return read_json(commands)['commands'], SAFE_COMMANDS
    if not policy_sha256 or not re.fullmatch(r'[0-9a-fA-F]{64}',policy_sha256):
        die('Project policy requires an explicit reviewed SHA-256')
    raw=Path(policy).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=policy_sha256.lower(): die('Project policy digest mismatch')
    obj=json.loads(raw.decode('utf-8-sig'))
    extra=obj.get('commands')
    if not isinstance(extra,dict) or not extra: die('Invalid project policy')
    combined=dict(SAFE_COMMANDS)
    for key,argv in extra.items():
        if not isinstance(key,str) or not re.fullmatch(r'[a-z][a-z0-9-]{2,63}',key) or key in combined:
            die('Invalid or conflicting policy command ID')
        if not isinstance(argv,list) or not argv or any(not isinstance(a,str) or not a or '\x00' in a for a in argv):
            die('Invalid policy argv')
        if Path(argv[0]).is_absolute() or '/' in argv[0] or '\\' in argv[0]:
            die('Policy executable must use a PATH command')
        combined[key]=argv
    return read_json(commands)['commands'], combined

def gate(run,commands,allow,task=None,policy=None,policy_sha256=None):
    if not allow: die('Refusing to execute commands: --allow-exec required')
    if not task: die('Gate requires explicit --task')
    data=load(run)
    t=task_get(data,task)
    if t['status']!='ACTIVE': die('Task must be ACTIVE')
    w=Path(t['worktree']).resolve()
    if not w.is_dir() or git('branch','--show-current',cwd=w)!=t['branch']: die('Invalid worktree')
    if git('status','--porcelain',cwd=w): die('Commit and clean worktree before gate')
    head=git('rev-parse','HEAD',cwd=w)
    changed=changed_files(w,t['base'],head)
    if not changed or any(not task_owns(f,t['paths']) for f in changed): die('Gate requires committed owned changes')
    configs,allowed=resolve_gate_commands(commands,policy,policy_sha256)
    if not isinstance(configs,list) or not configs: die('No validation commands')
    criteria=t['acceptance']
    if len(set(criteria))!=len(criteria) or not all(isinstance(x,str) and x.strip() for x in criteria): die('Invalid acceptance criteria')
    names=set(); normalized=[]
    for c in configs:
        name=c.get('name'); command_id=c.get('command_id'); argv=c.get('argv')
        if not isinstance(name,str) or not name or name in names: die('Duplicate/invalid gate name')
        names.add(name)
        if command_id not in allowed: die('Command not in trusted allowlist: '+repr(command_id))
        expected=allowed[command_id]
        if argv is not None and argv!=expected: die('argv differs from trusted allowlist')
        normalized.append((name,expected,c.get('acceptance')))
    covered={criterion for _,_,items in normalized for criterion in (items if isinstance(items,list) else [])}
    if set(criteria)-covered: die('Unverified acceptance criteria: '+repr(sorted(set(criteria)-covered)))
    if any(not isinstance(items,list) or not items or any(x not in criteria for x in items) for _,_,items in normalized): die('Each gate must map to actual acceptance criteria')
    results=[]
    for name,argv,items in normalized:
        if not (shutil.which(argv[0]) or Path(argv[0]).is_file()): die('Executable unavailable: '+argv[0])
        print('Running approved:',name,repr(argv),flush=True)
        try:
            p=subprocess.run(argv,cwd=w,capture_output=True,text=True,timeout=180,check=False)
            results.append(dict(name=name,command_id=next(k for k,v in allowed.items() if v==argv),acceptance=items,returncode=p.returncode,stdout=p.stdout[-4000:],stderr=p.stderr[-4000:]))
        except (OSError,subprocess.TimeoutExpired) as e:
            results.append(dict(name=name,acceptance=items,returncode=-1,error=str(e)))
    passed=all(r['returncode']==0 for r in results)
    save_json(file_for(run).parent/('gate-'+task+'.json'),dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),task=task,head=head,task_hash=task_hash(t),policy_sha256=policy_sha256,passed=passed,results=results))
    for r in results: print(r['name'],r['returncode'])
    if not passed: die('Gate failed; see per-task gate JSON')

def tokens(run=None):
    files=[file_for(run)] if run else sorted(RUNS.glob('*/plan.json'))
    for f in files:
        if not f.exists(): die('Run not found: '+str(f))
        data=read_json(f); payload=json.dumps(data,ensure_ascii=False)
        # Transparent approximation, not provider API billing tokens.
        estimate=(len(payload.encode('utf-8'))+3)//4
        print(f'{data["run_id"]}: {estimate} estimated tokens ({len(payload.encode("utf-8"))} UTF-8 bytes / 4). Not actual provider usage.')

def integrate(run,approve):
    if not approve: die('Integration requires explicit --approve')
    data=load(run)
    if any(t['status']!='DONE' for t in data['tasks']): die('All tasks must be DONE')
    if git('status','--porcelain'): die('Integration requires clean main worktree')
    original=git('branch','--show-current'); base=git('rev-parse','HEAD')
    for t in data['tasks']:
        current=git('rev-parse',t['branch'])
        if current!=t['head']: die('Branch changed since completion: '+t['id'])
    print('Merge target:',original,base)
    for t in data['tasks']:
        try:
            git('merge','--no-ff','--no-edit',t['branch'])
        except ValueError:
            print('STOP: merge conflict. Resolve manually or git merge --abort. Previous merges may already be committed.')
            raise
        t['status']='MERGED'
        save_json(file_for(run),data)
        print('Merged',t['id'])
    print('Integration complete; rerun full tests. No push/deploy performed.')

def main():
    p=argparse.ArgumentParser(); subs=p.add_subparsers(dest='cmd',required=True)
    subs.add_parser('validate'); a=subs.add_parser('init');a.add_argument('--project',required=True)
    a=subs.add_parser('plan'); a.add_argument('--file',required=True)
    a=subs.add_parser('status');a.add_argument('--run')
    for cmd in ('worktree','complete'):
        a=subs.add_parser(cmd);a.add_argument('--run',required=True);a.add_argument('--task',required=True)
        if cmd=='complete':a.add_argument('--evidence',required=True)
    a=subs.add_parser('gate');a.add_argument('--run',required=True);a.add_argument('--task',required=True);a.add_argument('--commands',required=True);a.add_argument('--allow-exec',action='store_true');a.add_argument('--policy');a.add_argument('--policy-sha256')
    a=subs.add_parser('tokens');a.add_argument('--run')
    a=subs.add_parser('integrate');a.add_argument('--run',required=True);a.add_argument('--approve',action='store_true')
    a=p.parse_args()
    try:
        if a.cmd=='validate': validate()
        elif a.cmd=='init':init(a.project)
        elif a.cmd=='plan':plan(a.file)
        elif a.cmd=='status':status(a.run)
        elif a.cmd=='worktree':worktree(a.run,a.task)
        elif a.cmd=='complete':complete(a.run,a.task,a.evidence)
        elif a.cmd=='gate':gate(a.run,a.commands,a.allow_exec,a.task,a.policy,a.policy_sha256)
        elif a.cmd=='tokens':tokens(a.run)
        elif a.cmd=='integrate':integrate(a.run,a.approve)
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:
        print('ERROR:',str(e),file=sys.stderr);sys.exit(2)
if __name__=='__main__': main()
