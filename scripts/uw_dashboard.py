#!/usr/bin/env python3
"""Read-only local live dashboard. Bind to 127.0.0.1 only; no remote access or writes."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,html,argparse
import workflow
ROOT=Path(__file__).resolve().parents[1]
PAGE='''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Universal AI Workflow — Live</title><style>body{font:16px system-ui;background:#0c1220;color:#e9eef7;margin:0;padding:28px}h1{font-size:24px}.muted{color:#a9b6cf}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:20px 0}.card{background:#182237;border:1px solid #33405a;border-radius:16px;padding:20px}small{color:#a9b6cf}.ok{color:#72d5ac}.fail{color:#ff8f9a}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}button{background:#e9eef7;border:0;border-radius:8px;padding:8px 16px}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:right;border-bottom:1px solid #33405a}</style><h1>Universal AI Workflow — Live Dashboard</h1><p class="muted">قراءة فقط · تحديث كل 3 ثوانٍ · لا يرسل معلومات إلى أي خادم</p><main id="app">جارٍ تحميل البيانات...</main><script>const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));async function tick(){try{const r=await fetch('/api/status',{cache:'no-store'});const d=await r.json();let runs=d.runs||[];document.querySelector('#app').innerHTML='<div class="cards">'+runs.map(x=>'<section class="card"><h2>'+esc(x.run_id)+'</h2><small>'+esc(x.tasks?.length||0)+' مهمة</small><table><tr><th>المهمة</th><th>الحالة</th></tr>'+((x.tasks||[]).map(t=>'<tr><td>'+esc(t.id)+'</td><td>'+esc(t.status)+'</td></tr>').join(''))+'</table><h3>آخر التقارير</h3><pre>'+esc((x.reports||[]).join('\n'))+'</pre></section>').join('')+'</div>';if(!runs.length)document.querySelector('#app').textContent='لا توجد خطط تشغيل بعد';}catch(e){document.querySelector('#app').textContent='تعذر قراءة الحالة: '+e.message}}tick();setInterval(tick,3000)</script></html>'''
def snapshot():
    result=[]
    for path in sorted((ROOT/'.ai/runs').glob('*/plan.json'))[:100]:
        try:
            obj=json.loads(path.read_text(encoding='utf8'))
            obj={'run_id':obj.get('run_id'),'tasks':[{'id':t.get('id'),'status':t.get('status')} for t in obj.get('tasks',[])],
                 'reports':[str(p.relative_to(ROOT)) for p in sorted(path.parent.glob('**/*report.json'))[-10:]]}
            result.append(obj)
        except (ValueError,OSError,KeyError):continue
    return {'runs':result}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Loopback-only binding does not prevent DNS rebinding without Host validation.
        host=self.headers.get('Host','')
        allowed=('127.0.0.1','localhost','[::1]')
        hostname=host.rsplit(':',1)[0] if ':' in host and not host.startswith('[') else (host.split(']')[0]+']' if host.startswith('[') else host)
        if hostname not in allowed:
            self.send_error(403, 'Untrusted Host');return
        if self.path=='/':payload=PAGE.encode();kind='text/html; charset=utf-8'
        elif self.path=='/api/status':payload=json.dumps(snapshot(),ensure_ascii=False).encode();kind='application/json; charset=utf-8'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):pass
def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8787);a=p.parse_args()
    if not 1024<=a.port<=65535:raise SystemExit('Port must be between 1024 and 65535')
    url='http://127.0.0.1:'+str(a.port);print('Dashboard:',url,flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()
