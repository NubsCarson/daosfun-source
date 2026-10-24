"""Local differential coverage of cosigner creation and rotation."""
from differential import *

def run_cosign(binary,case):
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,binary.read_bytes())
 payer=Keypair.from_seed(bytes([42])*32);vm.airdrop(payer.pubkey(),10**10);vm.set_account(CLOSE_AUTHORITY,Account(10**8,b'',Pubkey.default()))
 id=case.get('id',1);state,_=Pubkey.find_program_address([b'cosigner',bytes([id])],PROGRAM)
 steps=[('cosign_init',bytes([id])+bytes(payer.pubkey()))]
 if case.get('update'):steps.append(('cosign_update_signer',bytes([55])*32))
 if case.get('twice'):steps.append(steps[0])
 results=[]
 for index,(name,args) in enumerate(steps):
  if name=='cosign_update_signer' and case.get('non_pda_update'):
   saved=vm.get_account(state);state=Pubkey.from_bytes(bytes([91])*32);vm.set_account(state,saved)
  admin=payer.pubkey() if case.get('wrong_admin') else CLOSE_AUTHORITY
  keys=[AccountMeta(payer.pubkey(),True,True),AccountMeta(admin,not case.get('unsigned_admin'),False),AccountMeta(state,False,True)]
  if name=='cosign_init':keys.append(AccountMeta(Pubkey.default(),False,False))
  ix=Instruction(PROGRAM,hashlib.sha256(('global:'+name).encode()).digest()[:8]+args+bytes([index]),keys)
  tx=Transaction.new_unsigned(Message.new_with_blockhash([ix],payer.pubkey(),vm.latest_blockhash()))
  r=json.loads(vm.send_transaction(tx).to_json());a=vm.get_account(state)
  results.append({'error':r.get('err'),'account':a.to_json() if a else None,'logs':r.get('meta',r).get('logs')})
 return results

def main():
 cases=[{}, {'update':True,'non_pda_update':True}, {'id':0},{'id':255},{'update':True},{'twice':True},{'wrong_admin':True},{'unsigned_admin':True}]
 results=[]
 for case in cases:
  a=run_cosign(ROOT/'evidence/mainnet.so',case);b=run_cosign(ROOT/'target/deploy/dao_v1_recovered.so',case)
  same=[(r['error'],r['account']) for r in a]==[(r['error'],r['account']) for r in b]
  print(case,'PASS' if same else 'FAIL')
  if not same:print('original',a,'candidate',b)
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-cosign.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
