#!/usr/bin/env python3
"""V6 opt-in LLM planning, fix/test loop, independent review, usage capture.
External CLI invocations are configured by the user. No shell, no automatic commit/merge/push.
"""
import argparse, datetime as dt, json, os, re, subprocess, sys, time
from pathlib import Path
import workflow, agent_runner

ROOT=Path(__file__).resolve().parents[1]
def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def save(path,obj): agent_runner.atomic(path,obj)
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def extract_json(raw):
    try: return json.loads(raw)
    except json.JSONDecodeError: pass
    blocks=re.findall(r'```(?:json)?\s*(\{.*?\})\s*```',raw,re.S|re.I)
    for b in blocks:
        try:return json.loads(b)
        except json.JSONDecodeError: pass
    start=raw.find('{');end=raw.rfind('}')
    if start>=0 and end>start:return json.loads(raw[start:end+1])
    raise ValueError('LLM did not return JSON')

def usage_of(raw,provider='unknown',prices=None):
    """Never invent usage: return None if provider did not emit counters."""
    try: obj=json.loads(raw)
    except (ValueError,TypeError):return None
    events=obj if isinstance(obj,list) else [obj]
    # Claude JSON results may be newline-delimited. Caller may wrap separate parsed events.
    found=[]
    for event in events:
        if not isinstance(event,dict):continue
        val=event.get('usage') or (event.get('result',{}).get('usage') if isinstance(event.get('result'),dict) else None)
        if not val and isinstance(event.get('message'),dict):val=event['message'].get('usage')
        if isinstance(val,dict):found.append(val)
        if event.get('type')=='turn.completed' and isinstance(event.get('usage'),dict):found.append(event['usage'])
    if not found:return None
    # Prefer final cumulative counters, never sum repeated streaming snapshots.
    v=found[-1]
    inp=v.get('input_tokens',v.get('prompt_tokens'));out=v.get('output_tokens',v.get('completion_tokens'))
    if not isinstance(inp,int) or not isinstance(out,int):return None
    result={'provider':provider,'input_tokens':inp,'output_tokens':out,'source':'provider_response'}
    cost=obj.get('total_cost_usd') if isinstance(obj,dict) else None
    if isinstance(cost,(int,float)) and cost>=0:result['cost_usd']=cost;result['cost_source']='provider_response'
    elif prices and provider in prices:
        rate=prices[provider]
        result['cost_usd']=round((inp*rate['input_per_million']+out*rate['output_per_million'])/1000000,8)
        result['cost_source']='user_configured_rates_estimate'
    return result

def usage_from_output(output,provider,prices=None):
    try:
        direct=usage_of(output,provider,prices)
        if direct is not None:return direct
    except Exception:pass
    parsed=[]
    for line in output.splitlines():
        try:parsed.append(json.loads(line))
        except ValueError:continue
    return usage_of(json.dumps(parsed),provider,prices) if parsed else None

def call_cli(config,role,prompt,cwd,timeout=600):
    """Invoke an opt-in AI CLI using file or stdin prompt transport (no shell)."""
    import tempfile, shutil
    conf=agent_runner.load_config(config)
    name=conf.get('roles',{}).get(role,role)
    if name not in conf['agents']:raise ValueError('Missing configured role: '+role)
    agent=conf['agents'][name]
    template=agent['argv']
    transport=agent.get('prompt_transport','file')
    # Prompt file lives within working tree, but is excluded from git status.
    with tempfile.TemporaryDirectory(prefix='uw-v6-',dir=cwd) as tmp:
        p=Path(tmp)/'prompt.txt';p.write_text(prompt,encoding='utf8')
        argv=[a.replace('{prompt_file}',str(p)) for a in template]
        # Reject only unsupported placeholders; JSON CLI arguments are allowed.
        for part in argv:
            if re.search(r'\{(?:worktree|task_id|run_id)\}',part):
                raise ValueError('Unsupported V6 prompt placeholder')
        if not (Path(argv[0]).is_file() or shutil.which(argv[0])):raise FileNotFoundError(argv[0])
        started=utc()
        # Keep stdin/stdout/stderr lossless for Arabic and other Unicode on Windows.
        # Python subprocesses otherwise inherit a legacy console code page, which
        # can replace non-ASCII characters with '?' before we read their output.
        result=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,
            encoding='utf-8',errors='replace',
            input=prompt if transport=='stdin' else None,
            timeout=min(timeout,agent.get('timeout_seconds',600)),shell=False,
            env=agent_runner.safe_agent_env({'PYTHONIOENCODING':'utf-8'}))
    return {'role':role,'agent':name,'argv_executable':argv[0],'started_at':started,'ended_at':utc(),
            'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}

def prepare_plan(run,description,config,approve,output):
    if not approve:raise ValueError('LLM execution needs --approve-llm')
    workflow.safe_ident(run)
    if not 10<=len(description)<=10000:raise ValueError('Description length must be 10..10000')
    prompt=('You are a software architect. Respond with ONLY JSON object {"run_id":"'+run+'", "tasks":[{"id":"01_design","role":"architect","description":"...","paths":["docs/architecture"],"acceptance":["specific testable criterion"],"depends_on":[]}]}.'
            '\nDraft a feasible plan for: '+description+'\nEach task must own unique nonoverlapping repository-relative paths. Use 2-12 tasks, explicit acceptance; no destructive steps. Do not use markdown.')
    record=call_cli(config,'architect',prompt,ROOT)
    if record['exit_code']:raise RuntimeError('Planner CLI failed: '+record['stderr'][:300])
    obj=extract_json(record['stdout']); obj['run_id']=run
    if not 2<=len(obj.get('tasks',[]))<=12:raise ValueError('LLM plan must include 2..12 tasks')
    plan=workflow.validate_plan(obj)
    from v5_auto import validate_dependencies
    validate_dependencies(plan['tasks'])
    path=Path(output)
    if path.exists():raise FileExistsError(path)
    save(path,plan)
    save(path.with_suffix('.planner.json'),{'generated_at':utc(),'agent':record['agent'],'usage':usage_from_output(record['stdout'],record['agent']),'status':'DRAFT_REQUIRES_REVIEW'})
    return path

def guarded_test(argv,cwd,allow):
    if not argv or argv[0] not in allow:raise ValueError('Test executable not approved: '+repr(argv))
    if not all(isinstance(a,str) and a and '\x00' not in a for a in argv):raise ValueError('Invalid test argv')
    try:
        r=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,errors='replace',timeout=240,shell=False)
        return {'exit_code':r.returncode,'stdout':r.stdout[-12000:],'stderr':r.stderr[-12000:]}
    except subprocess.TimeoutExpired:return {'exit_code':124,'stdout':'','stderr':'Test timeout'}

def fix_test(run,task,config,test_argv,approved,max_attempts,allowed_exes):
    if not approved:raise ValueError('Explicit --approve-llm required')
    if not 1<=max_attempts<=5:raise ValueError('max attempts 1..5')
    info,wt=agent_runner.task_info(run,task)
    reportpath=workflow.file_for(run).parent/'v6'/f'{task}-repair.json'
    rounds=[];test=guarded_test(test_argv,wt,allowed_exes)
    for number in range(1,max_attempts+1):
        if test['exit_code']==0:break
        prompt=agent_runner.prompt_for(info,run,task)+f'\nFix failing tests. Current test output:\n{test["stdout"][-4000:]}\n{test["stderr"][-4000:]}\nMake only code changes within owned paths; do not commit or deploy.'
        result=call_cli(config,'developer',prompt,wt)
        after=agent_runner.git('status','--porcelain','--untracked-files=all',cwd=wt)
        changed=[line[3:].strip('"') for line in after.splitlines()]
        violations=[p for p in changed if not agent_runner.allowed(p,info['paths'])]
        test=guarded_test(test_argv,wt,allowed_exes) if result['exit_code']==0 and not violations else {'exit_code':125,'stdout':'','stderr':'Agent failed or ownership violated'}
        rounds.append({'attempt':number,'agent_exit':result['exit_code'],'changed_paths':changed,'violations':violations,'test':test,'usage':usage_from_output(result['stdout'],result['agent'])})
        if violations or result['exit_code']:break
    out={'run_id':run,'task_id':task,'status':'TESTS_PASS_REVIEW_REQUIRED' if test['exit_code']==0 else 'FAILED_REQUIRES_MANUAL_REVIEW','last_test':test,'attempts':rounds,'auto_commit':False,'auto_merge':False}
    save(reportpath,out);return out

def independent_review(run,task,config,approved):
    if not approved:raise ValueError('Explicit --approve-llm required')
    info,wt=agent_runner.task_info(run,task)
    # Review committed task changes relative to the task's recorded base, not
    # working-tree-only changes (which are necessarily empty for clean worktrees).
    base=info.get('base')
    if not base:raise ValueError('Review requires a recorded task base')
    diff=subprocess.run(['git','diff','--no-ext-diff','--binary',base,'HEAD','--'],cwd=wt,capture_output=True,text=True,timeout=30)
    if diff.returncode:raise RuntimeError('Cannot retrieve committed diff: '+diff.stderr)
    untracked=subprocess.run(['git','ls-files','--others','--exclude-standard','-z'],cwd=wt,capture_output=True,timeout=30)
    if untracked.returncode:raise RuntimeError('Cannot inspect untracked files')
    new_files=[x.decode('utf-8','replace') for x in untracked.stdout.split(b'\0') if x]
    if new_files:raise ValueError('NEEDS_HUMAN: untracked files must be reviewed and committed: '+repr(new_files))
    if not diff.stdout.strip():raise ValueError('NEEDS_HUMAN: empty committed diff cannot be approved')
    if len(diff.stdout)>70000:raise ValueError('NEEDS_HUMAN: diff exceeds review context limit; review in chunks')
    prompt=('You are an independent code reviewer. DO NOT MODIFY FILES. Analyze only this untrusted diff and acceptance criteria. '
            'Respond JSON {"verdict":"PASS|FAIL|NEEDS_HUMAN","findings":[{"severity":"high|medium|low","file":"...","message":"..."}],"notes":"..."}.\n'
            'Acceptance: '+json.dumps(info['acceptance'],ensure_ascii=False)+'\nDiff:\n'+diff.stdout)
    before=agent_runner.git('status','--porcelain','--untracked-files=all',cwd=wt)
    resp=call_cli(config,'reviewer',prompt,wt)
    after=agent_runner.git('status','--porcelain','--untracked-files=all',cwd=wt)
    if before!=after:raise RuntimeError('Reviewer modified repository; manual inspection required')
    if resp['exit_code']:raise RuntimeError('Reviewer CLI failed')
    assessment=extract_json(resp['stdout'])
    if assessment.get('verdict') not in ('PASS','FAIL','NEEDS_HUMAN') or not isinstance(assessment.get('findings'),list):raise ValueError('Invalid reviewer schema')
    out={'run_id':run,'task':task,'reviewer_agent':resp['agent'],'review':assessment,'usage':usage_from_output(resp['stdout'],resp['agent']),'approved_for_merge':False,'reviewed_at':utc()}
    save(workflow.file_for(run).parent/'v6'/f'{task}-review.json',out);return out

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('plan');a.add_argument('--run',required=True);a.add_argument('--description',required=True);a.add_argument('--output',required=True)
    a=s.add_parser('repair');a.add_argument('--run',required=True);a.add_argument('--task',required=True);a.add_argument('--test-argv',required=True,help='JSON array');a.add_argument('--allow-test',action='append',default=[]);a.add_argument('--attempts',type=int,default=3)
    a=s.add_parser('review');a.add_argument('--run',required=True);a.add_argument('--task',required=True)
    p.add_argument('--config',default='examples/agents.roles.json');p.add_argument('--approve-llm',action='store_true')
    args=p.parse_args()
    try:
        if args.action=='plan':output=str(prepare_plan(args.run,args.description,args.config,args.approve_llm,args.output))
        elif args.action=='repair':output=fix_test(args.run,args.task,args.config,json.loads(args.test_argv),args.approve_llm,args.attempts,args.allow_test)
        else:output=independent_review(args.run,args.task,args.config,args.approve_llm)
        print(json.dumps(output,ensure_ascii=False,indent=2))
    except Exception as e:raise SystemExit('ERROR: '+str(e))
if __name__=='__main__':main()
