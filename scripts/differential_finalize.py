"""Exercise migration-fee withdrawal and DAO state finalization."""
from probe_finalize import *
def main():
 cases=[{}, {'wallet_wrong_owner':True}, {'threshold':0},{'fee_percent':0},{'fee_percent':100},{'reserve':9999},{'threshold':10001,'reserve':10001},{'threshold':100001,'reserve':100001}]+[{'byte':[3,i,255 if i!=159 else 1]} for i in [8,40,72,159]]+[{'readonly':i} for i in [3,4,5,7,8,9]]+[{'alternate':i} for i in range(3,17)]
 results=[]
 for case in cases:
  a=finalize(case=case);b=finalize(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[l for l in b['logs'] if 'Error' in l])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-finalize.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
