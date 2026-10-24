"""Compare the legacy curve migration, including downstream CPI payloads."""
from probe_legacy_migration import *
import gzip
def main():
 cases=[{}, {'historical':True}]+[{'historical':True,'alternate':i} for i in range(1,31)]+[{'historical':True,'readonly':i} for i in [3,4,5,6,7,8,9,10,11,12,14,15,18,19,20,21]]+[{'historical':True,'byte':[3,i,v]} for i,v in [(8,0),(40,0),(72,0),(112,1),(113,1),(159,1)]]+[{'historical':True,'byte':[4,i,v]} for i,v in [(48,0),(80,0),(112,0),(121,1),(130,255),(162,255)]]+[{'historical':True,'qword':[4,32,n]} for n in [0,1,10**9,2*10**9,10**11]]+[{'historical':True,'truncate':n} for n in [112,130,162,169]]
 results=[]
 for case in cases:
  a=migrate(case=case);b=migrate(ROOT/'target/deploy/dao_v1_recovered.so',case)
  def cpis(x):
   m=x['raw'].get('meta',x['raw']);return [i['instruction'] for group in m['inner_instructions'] for i in group if i['stackHeight']==2]
  same=all(a[k]==b[k] for k in ['error','accounts']) and cpis(a)==cpis(b)
  print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[l for l in b['logs'] if 'Error' in l])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 with gzip.open(ROOT/'evidence/differential-legacy-migration.json.gz','wt') as output:
  json.dump(results,output,indent=2)
 assert all(r['matches'] for r in results)
if __name__=='__main__':main()
