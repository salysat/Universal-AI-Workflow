#!/usr/bin/env python3
"""Non-invasive detection: installed CLI != authenticated or authorized."""
import argparse,json,shutil,subprocess
from pathlib import Path
CANDIDATES={'claude':['claude'],'codex':['codex'],'gemini':['gemini'],'opencode':['opencode'],'aider':['aider'],'cursor':['cursor'],'copilot':['copilot']}
def discover():
    found={}
    for name,commands in CANDIDATES.items():
        for cmd in commands:
            path=shutil.which(cmd)
            if path:
                found[name]={'executable':path,'detected':True,'authenticated':'unknown','ready':False,
                             'reason':'Authentication, headless CLI flags, and permissions require manual verification'}
                break
    return found
def main():
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args()
    found=discover()
    if a.json: print(json.dumps({'detected':found,'note':'Detection does not invoke agents or confirm login.'},ensure_ascii=False,indent=2))
    else:
        print('Detected CLIs:',', '.join(found) or '(none)')
        print('A detected executable is not verified for unattended work. Configure argv and approval first.')
if __name__=='__main__':main()
