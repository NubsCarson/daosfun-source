"""Full DBC CPI plus onward transfers, with nonzero treasury starting balances."""
from probe_claim_dbc import *
def main():
 cases=[{}, {'base_fee':0,'quote_fee':0},{'base_fee':1,'quote_fee':0},{'base_fee':0,'quote_fee':1},{'base_fee':10001},{'quote_fee':10001},{'unsigned_fee':True}]+[{'byte':[0,i,255]} for i in [16,48,80]]+[{'alternate':i} for i in range(3,18)]+[{'readonly':i} for i in [0,4,5,6,8,9,10,11]]
 results=[]
 for case in cases:
  a=claim(case=case);b=claim(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[l for l in b['logs'] if 'Error' in l])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-claim-dbc.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
