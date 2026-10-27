#!/usr/bin/env python3
"""Import SARIF or simple scanner JSON into an editable, non-executing plan draft.
Optionally invoke a user-provided PowerShell scanner after explicit approval.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import re

RANK={"critical":4,"high":3,"error":3,"medium":2,"warning":2,"low":1,"note":1,"info":0}

def safe_path(raw):
    if not isinstance(raw,str): return None
    q=raw.replace("\\","/").removeprefix("./")
    if not q or q.startswith("/") or re.match(r"^[A-Za-z]:",q) or any(x in (".","..","") for x in q.split("/")):return None
    return q

def extract(doc):
    if isinstance(doc,dict) and doc.get("version")=="2.1.0" and "runs" in doc:
        for run in doc["runs"]:
            rules={x.get("id"):x for x in run.get("tool",{}).get("driver",{}).get("rules",[])}
            for hit in run.get("results",[]):
                rid=hit.get("ruleId","unknown"); rule=rules.get(rid,{})
                prop=rule.get("properties",{})
                lvl=prop.get("security-severity",hit.get("level","warning"))
                if str(lvl).replace(".","",1).isdigit():lvl="critical" if float(lvl)>=9 else "high" if float(lvl)>=7 else "medium" if float(lvl)>=4 else "low"
                locs=hit.get("locations",[])
                raw=(locs[0].get("physicalLocation",{}).get("artifactLocation",{}).get("uri","") if locs else "")
                yield dict(rule=rid,severity=str(lvl).lower(),path=raw,message=hit.get("message",{}).get("text",""))
    else:
        entries=doc if isinstance(doc,list) else doc.get("findings",doc.get("results",[]))
        for hit in entries:
            yield dict(rule=str(hit.get("rule",hit.get("id","unknown"))),severity=str(hit.get("severity",hit.get("level","medium"))).lower(),path=hit.get("path",hit.get("file","")),message=str(hit.get("message",hit.get("description",""))))

def draft(doc,run_id,minimum="high"):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",run_id):raise ValueError("invalid run id")
    cutoff=RANK[minimum]; grouped={}; rejected=[]
    for finding in extract(doc):
        if RANK.get(finding["severity"],0)<cutoff:continue
        path=safe_path(finding["path"])
        if not path:rejected.append(finding);continue
        grouped.setdefault(path,[]).append(finding)
    tasks=[]
    for i,(path,findings) in enumerate(sorted(grouped.items()),1):
        tasks.append(dict(id=f"audit_{i:03d}",description=f"Review and remediate {len(findings)} finding(s) at {path}",paths=[path],acceptance=["Security audit rerun shows no new Critical/High findings", "Project test suite passes"],audit_findings=findings))
    return {"run_id":run_id,"tasks":tasks,"excluded_findings":rejected,"note":"DRAFT ONLY: review ownership, paths and acceptance before workflow.py plan; no edits or agent execution"}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,required=True);a.add_argument("--run",required=True);a.add_argument("--output",type=Path,required=True)
    a.add_argument("--minimum",choices=list(RANK),default="high")
    a.add_argument("--scanner",type=Path,help="Explicit scanner .ps1 path (external, not bundled)")
    a.add_argument("--approve-scanner-execution",action="store_true")
    args=a.parse_args()
    if args.scanner:
        if not args.approve_scanner_execution:raise SystemExit("Scanner execution requires --approve-scanner-execution")
        if args.scanner.suffix.lower()!=".ps1" or not args.scanner.is_file():raise SystemExit("Expected existing .ps1 scanner")
        result=subprocess.run(["pwsh","-NoProfile","-File",str(args.scanner.resolve())],check=False,timeout=900)
        if result.returncode:raise SystemExit(f"Scanner failed with {result.returncode}")
    doc=json.loads(args.input.read_text(encoding="utf-8-sig"))
    out=draft(doc,args.run,args.minimum)
    if not out["tasks"]:raise SystemExit("No accepted findings: no plan generated")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Draft: {args.output} ({len(out['tasks'])} tasks; {len(out['excluded_findings'])} excluded unsafe locations)")
if __name__=="__main__":main()
