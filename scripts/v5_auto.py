#!/usr/bin/env python3
"""V5 role sessions: schedule sequential dependencies or parallel independent tasks, with evidence reporting.
No automatic commits, merges, deploys, arbitrary command execution or unapproved retries.
"""
import argparse,concurrent.futures,datetime as dt,json,os,time
from pathlib import Path
import workflow,agent_runner,ai_discovery

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def validate_dependencies(tasks):
    ids={t['id'] for t in tasks}
    graph={t['id']:t.get('depends_on',[]) for t in tasks}
    for key,deps in graph.items():
        if not isinstance(deps,list) or any(not isinstance(x,str) or x not in ids or x==key for x in deps):raise ValueError('Bad dependency for '+key)
    visiting=set();done=set()
    def visit(k):
        if k in visiting:raise ValueError('Dependency cycle: '+k)
        if k in done:return
        visiting.add(k)
        for d in graph[k]:visit(d)
        visiting.remove(k);done.add(k)
    for k in graph:visit(k)
    return graph

def schedule(tasks,max_workers=2):
    if not 1<=max_workers<=8:raise ValueError('max_workers must be 1..8')
    deps=validate_dependencies(tasks)
    todo={t['id'] for t in tasks};waves=[]
    while todo:
        ready=sorted(t for t in todo if all(d not in todo for d in deps[t]))
        if not ready:raise ValueError('No ready tasks')
        wave=ready[:max_workers];waves.append(wave);todo.difference_update(wave)
    return waves

def config_for_role(conf,role,fallback):
    roles=conf.get('roles',{})
    name=roles.get(role,fallback)
    if name not in conf['agents']:raise ValueError('No configured agent for role '+str(role)+': '+str(name))
    return name

def run(run_id,config,agent,max_workers,approve_worktrees,approve_agents,retries,dry_run=False):
    if retries<0 or retries>2:raise ValueError('retries must be 0..2')
    conf=agent_runner.load_config(config)
    data=workflow.load(run_id);tasks=data['tasks'];waves=schedule(tasks,max_workers)
    mapping={t['id']:config_for_role(conf,t.get('role','developer'),agent) for t in tasks}
    preview={'run_id':run_id,'waves':waves,'roles':{t['id']:t.get('role','developer') for t in tasks},
             'agents':mapping,'same_model_sessions_supported':True,'retry_limit':retries,
             'warning':'CLI binary detection != login; sessions are independent and can incur separate API cost.'}
    if dry_run or not approve_agents:
        print(json.dumps({'mode':'PREVIEW',**preview},ensure_ascii=False,indent=2));return preview
    started=now();results={};task_by_id={t['id']:t for t in tasks}
    for wave in waves:
        runnable=[]
        for tid in wave:
            t=task_by_id[tid]
            if any(results.get(d,{}).get('status')!='FINISHED_UNVERIFIED' for d in t.get('depends_on',[])):
                results[tid]={'task_id':tid,'status':'BLOCKED','reason':'Dependency did not finish successfully'};continue
            try:
                if t['status']=='PLANNED':
                    if not approve_worktrees:
                        results[tid]={'task_id':tid,'status':'SKIPPED','reason':'Worktree approval required'};continue
                    workflow.worktree(run_id,tid)
                elif t['status']!='ACTIVE':
                    results[tid]={'task_id':tid,'status':'SKIPPED','reason':'Task not PLANNED/ACTIVE'};continue
                runnable.append(tid)
            except Exception as e:
                results[tid]={'task_id':tid,'status':'ERROR','reason':str(e)}
        def task_job(tid):
            history=[]
            for attempt in range(retries+1):
                try:
                    record=agent_runner.run_one(run_id,tid,mapping[tid],config,True)
                except Exception as e:
                    record={'task_id':tid,'status':'ERROR','reason':str(e),'agent':mapping[tid]}
                history.append(record)
                # Never retry after changes: next run requires human inspection of dirty worktree.
                if record['status']=='FINISHED_UNVERIFIED' or record.get('changed_paths') or record['status']=='BLOCKED':break
            last=dict(history[-1]);last['attempts']=history;last['attempt_count']=len(history)
            return last
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            for tid,result in zip(runnable,pool.map(task_job,runnable)):
                results[tid]=result
    ordered=[results[t['id']] for t in tasks]
    report={'run_id':run_id,'started_at':started,'finished_at':now(),'preview':preview,'results':ordered,
            'count_by_status':{k:sum(r['status']==k for r in ordered) for k in sorted({r['status'] for r in ordered})},
            'usage':{'actual_tokens':None,'actual_cost':None,'measurement':'unavailable: provider billing/token data not integrated'},
            'approvals':{'cli_execution':True,'worktrees':approve_worktrees,'auto_commit':False,'auto_merge':False,'auto_push':False},
            'next_steps':['Inspect changes and logs','Commit changes after review','Run acceptance gate','Verify completion manually']}
    out=workflow.file_for(run_id).parent/'auto_v5';out.mkdir(parents=True,exist_ok=True)
    workflow.save_json(out/'report.json',report)
    lines=[f'# Auto V5 report: {run_id}','','## Execution',f'- Started: {started}',f'- Finished: {report["finished_at"]}',
           f'- Waves: {json.dumps(waves)}','','## Results']
    for r in ordered:
        lines.extend(['',f'### {r["task_id"]}: {r["status"]}',f'- CLI: {r.get("agent",mapping[r["task_id"]])}',
                      f'- Attempts: {r.get("attempt_count",0)}',f'- Changed paths: {", ".join(r.get("changed_paths",[])) or "none"}',
                      f'- Errors: {r.get("reason",r.get("ownership_violations","none"))}',f'- Logs: {r.get("logs",{})}'])
    lines.extend(['','## Usage','- Tokens and cost: not available unless provider emits machine-readable data; not guessed.','','## Required approvals','- Review changes and approval gates before commit / merge / push.'])
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('Wrote',out/'report.md');return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--config',default='examples/agents.roles.json');p.add_argument('--agent',default='local')
    p.add_argument('--max-workers',type=int,default=2);p.add_argument('--retries',type=int,default=0)
    p.add_argument('--approve-worktrees',action='store_true');p.add_argument('--approve-agents',action='store_true')
    a=p.parse_args()
    try:
        report=run(a.run,a.config,a.agent,a.max_workers,a.approve_worktrees,a.approve_agents,a.retries)
        if 'results' in report and any(r['status']!='FINISHED_UNVERIFIED' for r in report['results']):raise SystemExit(1)
    except (ValueError,FileNotFoundError,KeyError,OSError) as e:raise SystemExit('ERROR: '+str(e))
if __name__=='__main__':main()
