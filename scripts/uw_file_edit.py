#!/usr/bin/env python3
"""Safe, minimal edits to UTF-8 text, JSON and CSV. No macros, execution, PDF/Office claims."""
import argparse,csv,io,json,hashlib,sys
from pathlib import Path

def edit(root,source,mode,old=None,new=None,key=None,value=None,expected_hash=None):
    root=Path(root).resolve();p=(root/source).resolve()
    if not p.is_relative_to(root) or not p.is_file() or p.is_symlink():raise ValueError('unsafe or missing file')
    if p.stat().st_size>2_000_000:raise ValueError('too large')
    raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if expected_hash and digest!=expected_hash:raise ValueError('source changed: hash mismatch')
    text=raw.decode('utf-8-sig')
    if mode=='replace':
        if not old or text.count(old)!=1:raise ValueError('old text must match exactly once')
        result=text.replace(old,new if new is not None else '')
    elif mode=='json-set':
        obj=json.loads(text)
        if not isinstance(obj,dict) or not key or not key in obj:raise ValueError('existing root JSON key required')
        obj[key]=json.loads(value);result=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    elif mode=='csv-set':
        reader=csv.DictReader(io.StringIO(text));rows=list(reader);fields=reader.fieldnames
        if not fields or key not in fields or not rows:raise ValueError('existing CSV column and rows required')
        if len(rows)!=1:raise ValueError('CSV edit supports only single-row files; avoid ambiguous mutation')
        rows[0][key]=value
        out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);result=out.getvalue()
    else:raise ValueError('unsupported editing format')
    return p,digest,result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('replace','json-set','csv-set'));ap.add_argument('file');ap.add_argument('--root',default='.');ap.add_argument('--old');ap.add_argument('--new');ap.add_argument('--key');ap.add_argument('--value');ap.add_argument('--sha256');ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    try:
        p,h,result=edit(a.root,a.file,a.mode,a.old,a.new,a.key,a.value,a.sha256)
        if a.apply:
            backup=p.with_name(p.name+'.uwbak')
            if backup.exists():raise ValueError('backup exists; preserve it')
            backup.write_bytes(p.read_bytes());p.write_text(result,encoding='utf-8')
        print(json.dumps({'file':str(p),'before_sha256':h,'after_sha256':hashlib.sha256(result.encode()).hexdigest(),'applied':a.apply,'backup':str(p)+'.uwbak' if a.apply else None},ensure_ascii=False));return 0
    except (OSError,ValueError,UnicodeError,json.JSONDecodeError) as ex:print('ERROR:',ex,file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
