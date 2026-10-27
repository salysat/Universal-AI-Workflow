#!/usr/bin/env python3
"""Provider-independent, in-session team state protocol. No AI API, shell or network calls.
The SAME assistant runs role prompts sequentially, unless its host natively supports subagents.
"""
import argparse, json, hashlib, datetime as dt
from pathlib import Path

ROLES=('architect','developer','tester','reviewer')
PROMPTS={
 'architect':'Analyze requirements and relevant files only. Define acceptance criteria, affected files, risks and minimal plan. Never claim implementation.',
 'developer':'Implement approved plan with minimal changes. Record changed files and evidence. Do not claim tests were run.',
 'tester':'Run available targeted tests; record command, exit code and observable results. Mark unrun tests explicitly.',
 'reviewer':'Independently inspect diff, tests, risks, permission and completeness. Reject without evidence or when unsafe.'}
MAX=1_000_000

def root_path(root, name):
    root=Path(root).resolve(); p=(root/name).resolve()
    if not p.is_relative_to(root): raise ValueError('workspace escape')
    return p

def load(root):
    p=root_path(root,'.ai/internal-team.json')
    if not p.exists():return {'schema':1,'tasks':{}}
    d=json.loads(p.read_text(encoding='utf-8'))
    if d.get('schema')!=1 or not isinstance(d.get('tasks'),dict):raise ValueError('invalid team state')
    return d

def save(root, state):
    p=root_path(root,'.ai/internal-team.json');p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(p)

def create(root,task_id,goal,files):
    if not task_id or not all(c.isalnum() or c in '_-' for c in task_id):raise ValueError('invalid task id')
    if not goal.strip():raise ValueError('goal required')
    state=load(root)
    if task_id in state['tasks']:raise ValueError('task already exists')
    for f in files:root_path(root,f)
    state['tasks'][task_id]={'goal':goal,'files':files,'next_role':'architect','steps':{},'status':'active', 'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    save(root,state)
    return state['tasks'][task_id]

def prompt(root,task_id):
    t=load(root)['tasks'][task_id]
    role=t['next_role']
    if role is None:return {'status':t['status'],'prompt':None}
    return {'role':role,'instructions':PROMPTS[role], 'goal':t['goal'],'related_files':t['files'], 'prior_evidence':t['steps'], 'rule':'Perform this role using the current host assistant. This CLI does not call an AI or spawn parallel agents. Use host-native subagents only if supported; never pretend independence.'}

def record(root,task_id,role,report,evidence,approved=False):
    state=load(root);t=state['tasks'][task_id]
    if role!=t['next_role']:raise ValueError('out-of-order role; expected '+str(t['next_role']))
    if not report.strip():raise ValueError('report required')
    if len(report)>MAX:raise ValueError('report too large')
    if role in ('tester','reviewer') and not evidence.strip():raise ValueError('test and review evidence required')
    t['steps'][role]={'report':report,'evidence':evidence,'approved':bool(approved),'time_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    if role=='reviewer':
        t['status']='completed' if approved else 'needs_revision';t['next_role']=None if approved else 'developer'
    else:t['next_role']=ROLES[ROLES.index(role)+1]
    save(root,state);return {'status':t['status'],'next_role':t['next_role']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('start');p.add_argument('task_id');p.add_argument('goal');p.add_argument('--files',nargs='*',default=[])
    p=sub.add_parser('next');p.add_argument('task_id')
    p=sub.add_parser('record');p.add_argument('task_id');p.add_argument('role',choices=ROLES);p.add_argument('--report',required=True);p.add_argument('--evidence',default='');p.add_argument('--approve',action='store_true')
    sub.add_parser('status')
    a=ap.parse_args()
    try:
        if a.cmd=='start':v=create(a.root,a.task_id,a.goal,a.files)
        elif a.cmd=='next':v=prompt(a.root,a.task_id)
        elif a.cmd=='record':v=record(a.root,a.task_id,a.role,a.report,a.evidence,a.approve)
        else:v=load(a.root)
        print(json.dumps(v,ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as ex:print('ERROR:',ex);return 2
if __name__=='__main__':raise SystemExit(main())
