#!/usr/bin/env python3
"""Generate a safe editable *draft* plan from Arabic/English description; no LLM calls."""
import argparse,json,re
from pathlib import Path
import workflow

def draft(run,description,paths=None):
    workflow.safe_ident(run)
    description=description.strip()
    if not 10<=len(description)<=10000:raise ValueError('Description length must be 10..10000 chars')
    if paths is None:paths=['docs/architecture','src/implementation','tests/implementation','docs/review']
    if len(paths)!=4:raise ValueError('Expected four ownership paths')
    for p in paths:workflow.owner_path(p)
    roles=[('architect','Design and write the implementation plan'),('developer','Implement the approved design'),('tester','Add and run automated tests'),('reviewer','Review security, correctness, and tests')]
    tasks=[]
    for i,((role,objective),path) in enumerate(zip(roles,paths),1):
        tasks.append({'id':f'{i:02d}_{role}','description':f'{objective}. User request: {description}',
                      'paths':[path],'acceptance':[f'Manually define and verify acceptance for {role}'],
                      'role':role,'depends_on':([f'{i-1:02d}_{roles[i-2][0]}'] if i>1 else [])})
    return workflow.validate_plan({'run_id':run,'tasks':tasks})
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--description',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();out=Path(a.output)
    if out.exists():raise SystemExit('Refusing to overwrite plan draft: '+str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(draft(a.run,a.description),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DRAFT ONLY:',out,'Review paths, dependencies, acceptance criteria before `workflow.py plan`.')
if __name__=='__main__':main()
