"""Compare successful fundraising and boundary cases with real dependency code."""
from probe_start_raise import *
def main():
 results=[]
 for duration,case in [(500,{'whitelist_signer':False}),(500,{'whitelist_signer':True}),(604801,{'dao_token_legacy':True}),(604801,{'funding_token_2022':True}),(604801,{'whitelist_signer':False}),(604801,{'whitelist_signer':True}),(500,{'curve':True}),(604800,{}),(604801,{}),(0,{}),(1,{}),(2**32-1,{}),(500,{'goal':0}),(500,{'goal':1001}),(500,{'goal':9}),(500,{'closed':1}),(500,{'started':1}),(500,{'wrong_admin':True}),(500,{'missing_admin_token':True}),(500,{'missing_admin_fund':True}),(500,{'readonly_state':True})]+[(500,c) for c in [{'state_byte':40},{'state_byte':72}]+[{'alternate':i} for i in [4,5,6,8,9,10]]+[{'readonly':i} for i in [4,5,6,8,9,10]]]:
  a=probe(duration,case,ROOT/'evidence/mainnet.so',False);b=probe(duration,case,ROOT/'target/deploy/dao_v1_recovered.so',False);same=all(a[k]==b[k] for k in ['error','accounts']);print(duration,case,'PASS' if same else 'FAIL')
  if not same:print(a['error'],b['error'],[x for x in b['logs'] if 'Error' in x])
  results.append({'duration':duration,'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-start-raise.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
