#!/usr/bin/env python3
"""Generate synchronized assistant entrypoints from commands/registry.json.
Only files under owned uw-* paths are generated. --check compares without writing.
"""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def expected(root=ROOT):
    data=json.loads((root/'commands/registry.json').read_text(encoding='utf8'))
    out={}
    for name,v in sorted(data['commands'].items()):
        body=v['body']; desc=v['description']
        out[f'.claude/commands/{name}.md']=body
        out[f'.cursor/commands/{name}.md']=body
        out[f'.opencode/commands/{name}.md']=body
        out[f'.gemini/commands/{name}.toml']='description = '+json.dumps(desc,ensure_ascii=False)+'\nprompt = '+json.dumps(body.replace('$ARGUMENTS','{{args}}'),ensure_ascii=False)+'\n'
        out[f'.github/prompts/{name}.prompt.md']='---\ndescription: '+desc+'\n---\n'+body
        out[f'.agents/skills/{name}/SKILL.md']='---\nname: '+name+'\ndescription: '+desc+'\n---\n'+body
    return out

def generate(root=ROOT,check=False):
    mismatches=[]
    for rel,content in expected(root).items():
        dest=root/rel
        if not dest.is_file() or dest.read_text(encoding='utf8')!=content:
            mismatches.append(rel)
            if not check:
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(content,encoding='utf8')
    return mismatches

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    mismatches=generate(check=args.check)
    print(('OUT OF SYNC' if args.check else 'GENERATED')+': '+str(len(mismatches))+' files')
    if args.check and mismatches:
        print('\n'.join(mismatches));raise SystemExit(1)
