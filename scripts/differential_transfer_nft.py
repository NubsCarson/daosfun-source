"""Compare ownership changes, PDA checks, and identity relationships."""
from probe_transfer_nft import *
def main():
 cases=[{}]+[{'byte':[3,i,0 if i==159 else 255]} for i in [8,40,72,159,127]]+[{'byte':[4,168,255]},{'byte':[4,200,255]},{'byte':[7,8,255]},{'byte':[7,40,255]},{'byte':[6,0,255]},{'byte':[6,32,255]},{'byte':[9,16,255]},{'byte':[9,48,255]},{'byte':[9,80,255]}]+[{'alternate':i} for i in [3,4,5,6,7,8,9]]+[{'readonly':i} for i in [3,4,6,7,9]]
 results=[]
 for case in cases:
  a=probe(case=case);b=probe(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],b['logs'])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-transfer-nft.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
