"""Compare direct pool creation using a captured production DBC configuration."""
from probe_bonding_init import *
def main():
 cases=[{}, {'name':''},{'name':'雪 DAO'}, {'name':'A'*64}]+[{'byte':[4,i,255]} for i in [0,16,48,80]]+[{'byte':[5,i,255]} for i in [0,7]]+[{'alternate':i} for i in range(3,17)]+[{'readonly':i} for i in [1,3,6,7,8,9]]
 results=[]
 for case in cases:
  a=initialize_bonding(case=case);b=initialize_bonding(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']) and [l for l in a['logs'] if l.startswith(f'Program {DBC} invoke')] == [l for l in b['logs'] if l.startswith(f'Program {DBC} invoke')];print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[l for l in b['logs'] if 'Error' in l])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-bonding-init.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
