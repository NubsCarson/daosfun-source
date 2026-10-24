"""Compare pool creation with historical DAMM, and current dependency rejection."""
from probe_init_curve import *
def main():
 historical=[{'historical':True,'amount':n} for n in [0,1,999,10**8,10**9,10**10]]
 cases=historical+[{}, {'historical':True,'byte':[4,171,2]}]+[{'historical':True,'alternate':i} for i in range(1,24)]+[{'historical':True,'readonly':i} for i in [3,5,6,7,8,9,10,11,12,13,15,16,19,20,21,22]]+[{'historical':True,'byte':[3,i,v]} for i,v in [(8,0),(40,0),(72,0),(112,1),(113,1),(159,1)]]+[{'historical':True,'byte':[4,i,0]} for i in [8,40,72,136,137,138]]+[{'historical':True,'byte':[14,i,0]} for i in [16,48,80]]
 results=[]
 for case in cases:
  a=init_curve(case=case);b=init_curve(ROOT/'target/deploy/dao_v1_recovered.so',case)
  same=all(a[k]==b[k] for k in ['error','accounts'])
  # The target's direct CPI data and account ordering should agree too.
  def cpis(x):
   m=x['raw'].get('meta',x['raw']);return [i['instruction'] for group in m['inner_instructions'] for i in group if i['stackHeight']==2]
  same=same and cpis(a)==cpis(b)
  print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[l for l in b['logs'] if 'Error' in l])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-init-curve.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
