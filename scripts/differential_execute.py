"""Differential CPI behavior using only local VM balances and captured fixtures."""
from differential import *
import struct

def execute(binary,case):
 accounts=json.loads((ROOT/'evidence/full-account-samples.json').read_text())['accounts'];accounts.update(json.loads((ROOT/'evidence/related-accounts.json').read_text()))
 k,a=next((k,a) for k,a in accounts.items() if a and a['space']==256);data=bytearray(base64.b64decode(a['data'][0]));admin=Pubkey.from_bytes(bytes(data[8:40]));mint=Pubkey.from_bytes(bytes(data[40:72]));state=Pubkey.from_string(k)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,binary.read_bytes())
 for k,a in accounts.items():
  if a:vm.set_account(Pubkey.from_string(k),Account(a['lamports'],base64.b64decode(a['data'][0]),Pubkey.from_string(a['owner']),a['executable'],a['rentEpoch']))
 payer=Keypair.from_seed(bytes([42])*32);vm.airdrop(payer.pubkey(),10**10)
 wallet,_=Pubkey.find_program_address([b'wallet',bytes(mint)],PROGRAM);vm.set_account(wallet,Account(10**9,b'',Pubkey.default()))
 cosign=Pubkey.from_string(next(k for k,a in accounts.items() if a and a['space']==41));cosigner=Pubkey.from_bytes(base64.b64decode(accounts[str(cosign)]['data'][0])[9:41]);vm.set_account(cosigner,Account(10**8,b'',Pubkey.default()))
 if case.get('wrong_state_mint'):data[40:72]=bytes([99])*32
 if case.get('wrong_wallet_owner'):vm.set_account(wallet,Account(10**9,b'',PROGRAM))
 data[112]=int(case.get('closed',False));data[113]=int(case.get('redemption',False));data[114:122]=struct.pack('<q',case.get('expiry',-1))
 if case.get('delegate'):
  data= data[:122]+bytes([1])+bytes(payer.pubkey())+data[123:224]
 vm.set_account(state,Account(10**8,bytes(data),PROGRAM))
 authority=payer.pubkey() if case.get('outsider') or case.get('delegate') else admin
 if case.get('wrong_cosigner'):cosigner=payer.pubkey()
 if case.get('other_cosign_id'):
  cosign,_=Pubkey.find_program_address([b'cosigner',bytes([1])],PROGRAM);vm.set_account(cosign,Account(10**8,hashlib.sha256(b'account:CosignState').digest()[:8]+bytes([1])+bytes(cosigner),PROGRAM))
 target=payer.pubkey() if case.get('nonexecutable_target') else Pubkey.default()
 metas=[AccountMeta(authority,not case.get('unsigned'),not case.get('readonly_authority')),AccountMeta(mint,False,False),AccountMeta(state,False,not case.get('readonly_state')),AccountMeta(wallet,False,True),AccountMeta(target,False,False),AccountMeta(cosigner,True,False),AccountMeta(cosign,False,False)]
 metas += [AccountMeta(wallet,False,True),AccountMeta(payer.pubkey(),False,True)]
 raw=struct.pack('<IQ',2,case.get('amount',100))
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:execute_invoke').digest()[:8]+struct.pack('<I',len(raw))+raw,metas)
 tx=Transaction.new_unsigned(Message.new_with_blockhash([ix],payer.pubkey(),vm.latest_blockhash()));r=json.loads(vm.send_transaction(tx).to_json())
 return {'error':r.get('err'),'state':vm.get_account(state).data.hex(),'wallet':vm.get_account(wallet).lamports,'logs':r.get('meta',r).get('logs')}

def main():
 cases=[{}, {'wrong_state_mint':True},{'wrong_wallet_owner':True,'amount':0}, {'expiry':0},{'expiry':9999999999},{'closed':True},{'redemption':True},{'delegate':True},{'outsider':True},{'wrong_cosigner':True},{'unsigned':True},{'readonly_authority':True},{'readonly_state':True},{'other_cosign_id':True},{'amount':10**10},{'nonexecutable_target':True}]
 results=[]
 for case in cases:
  a=execute(ROOT/'evidence/mainnet.so',case);b=execute(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','state','wallet']);print(case,'PASS' if same else 'FAIL')
  if not same:print('original',a,'candidate',b)
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-execute.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
