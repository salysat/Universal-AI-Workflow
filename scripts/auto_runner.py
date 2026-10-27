#!/usr/bin/env python3
"""Plan-driven orchestration with explicit approvals and JSON/Markdown reports.

This command never auto-commits, merges, pushes or deploys. CLI agents are
external executables; executing them requires explicit operator approval.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import sys
import traceback

import workflow
import agent_runner

ROOT=Path(__file__).resolve().parents[1]

def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()

def describe(run,agent,max_workers):
    data=workflow.load(run)
    tasks=data['tasks']
    assignments=[]
    for t in tasks:
        assignments.append({'task_id':t['id'],'status':t['status'],'paths':t['paths'],
                            'acceptance':t['acceptance'],'agent':t.get('agent') or agent})
    return {'run_id':run,'max_workers':max_workers,'assignments':assignments}

def execute(run,agent,config,max_workers,approve_worktrees,approve_agents):
    if max_workers<1 or max_workers>8: raise ValueError('max-workers must be 1..8')
    conf=agent_runner.load_config(config)
    preview=describe(run,agent,max_workers)
    for t in preview['assignments']:
        if t['agent'] not in conf['agents']:
            raise ValueError('Agent not configured: '+t['agent'])
    if not approve_agents:
        print(json.dumps({'mode':'PREVIEW','requires':'--approve-agents (and --approve-worktrees for planned tasks)',**preview},ensure_ascii=False,indent=2))
        return None
    started=stamp()
    records=[]
    # Each task has exclusive path ownership, verified by workflow.load().
    for t in preview['assignments']:
        try:
            if t['status']=='PLANNED':
                if not approve_worktrees:
                    records.append({'task_id':t['task_id'],'agent':t['agent'],'status':'SKIPPED','reason':'Requires --approve-worktrees'})
                    continue
                workflow.worktree(run,t['task_id'])
            elif t['status']!='ACTIVE':
                records.append({'task_id':t['task_id'],'agent':t['agent'],'status':'SKIPPED','reason':'Task not PLANNED or ACTIVE'})
        except Exception as exc:
            records.append({'task_id':t['task_id'],'agent':t['agent'],'status':'ERROR','reason':str(exc)})
    excluded={r['task_id'] for r in records}
    eligible=[t for t in preview['assignments'] if t['task_id'] not in excluded]
    def run_task(t):
        try:
            return agent_runner.run_one(run,t['task_id'],t['agent'],config,True)
        except Exception as exc:
            return {'task_id':t['task_id'],'agent':t['agent'],'status':'ERROR','reason':str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        records += list(pool.map(run_task,eligible))
    by_id={r['task_id']:r for r in records}
    ordered=[by_id[t['task_id']] for t in preview['assignments']]
    counts={s:sum(r['status']==s for r in ordered) for s in ('FINISHED_UNVERIFIED','FAILED','BLOCKED','ERROR','SKIPPED')}
    report={'run_id':run,'started_at':started,'finished_at':stamp(),'policy':{
        'agent_execution_approved':True,'worktree_creation_approved':approve_worktrees,
        'auto_commit':False,'auto_merge':False,'auto_push':False,'auto_deploy':False},
        'counts':counts,'plan':preview,'results':ordered,
        'next_steps':['Review agent changes and logs','Commit authorized changes manually',
                      'Run workflow gate with approved validation commands',
                      'Complete each verified task; integrate only with explicit approval'],
        'warning':'FINISHED_UNVERIFIED is not DONE. Agents are not sandboxed; review all changes.'}
    folder=workflow.file_for(run).parent/'auto'
    folder.mkdir(parents=True,exist_ok=True)
    workflow.save_json(folder/'report.json',report)
    lines=[f'# UW Auto Report — {run}','',f'Started: {started}',f'Finished: {report["finished_at"]}','',
           '## Summary','']+[f'- {s}: {n}' for s,n in counts.items()]+['','## Tasks','']
    for r in ordered:
        lines.extend([f'### {r["task_id"]} — {r["status"]}',f'- Agent: {r["agent"]}',
                      f'- Exit code: {r.get("exit_code","n/a")}',
                      f'- Changed paths: {", ".join(r.get("changed_paths",[])) or "none"}',
                      f'- Ownership violations: {", ".join(r.get("ownership_violations",[])) or "none"}',
                      f'- Reason: {r.get("reason","n/a")}',
                      f'- Logs: {r.get("logs",{})}',''])
    lines.extend(['## Next steps','']+['- '+s for s in report['next_steps']]+['','**Warning:** '+report['warning']])
    (folder/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Auto report:',folder/'report.md')
    print('Counts:',counts)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    p.add_argument('--agent',required=True,help='Default agent for tasks without an agent field')
    p.add_argument('--config',default='examples/agents.example.json')
    p.add_argument('--max-workers',type=int,default=2)
    p.add_argument('--approve-worktrees',action='store_true')
    p.add_argument('--approve-agents',action='store_true')
    a=p.parse_args()
    try:
        r=execute(a.run,a.agent,a.config,a.max_workers,a.approve_worktrees,a.approve_agents)
        if r and any(v for k,v in r['counts'].items() if k!='FINISHED_UNVERIFIED'):sys.exit(1)
    except (ValueError,KeyError,FileNotFoundError,OSError,json.JSONDecodeError) as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
