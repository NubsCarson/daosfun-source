"""Capture explicitly referenced public frontend assets for chain/contract discovery."""
import concurrent.futures,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'evidence/web';out.mkdir(parents=True,exist_ok=True)
base='https://clank.trade/assets/'
seen=set();queue={'index-Cet8iNnC.js'}
def fetch(name):
 p=out/name
 if not p.exists():
  subprocess.run(['curl','-L','--fail','--silent','--show-error','--max-time','30',base+name,'-o',str(p)],check=True)
 return name,p.read_text()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 while queue and len(seen)<180:
  batch=sorted(queue-seen);queue=set()
  for name,source in pool.map(fetch,batch):
   seen.add(name)
   for dep in re.findall(r'["\'`](?:\./|/assets/|assets/)([A-Za-z0-9_-]+\.js)["\'`]',source):
    if dep not in seen:queue.add(dep)
rows=[dict(url=base+n,bytes=(out/n).stat().st_size,sha256=hashlib.sha256((out/n).read_bytes()).hexdigest()) for n in sorted(seen)]
(out/'asset-manifest.json').write_text(json.dumps(rows,indent=2)+'\n');print('Captured',len(rows),'referenced JS assets')
for n in sorted(seen):
 s=(out/n).read_text()
 for term in ['robinhood','Robinhood','factoryAddress','bondingCurve','4FqThZWv','rpcUrls']:
  for m in list(re.finditer(re.escape(term),s))[-4:]:print(n,term,s[max(0,m.start()-100):m.end()+200])
