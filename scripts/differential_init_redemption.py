"""Differential redemption activation and carry calculation."""
from differential_burn import *

def activate(binary,case):
 token_program=Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb') if case.get('token_2022') else TOKEN
 payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);funding=Pubkey.from_bytes(bytes([51])*32);wallet,_=Pubkey.find_program_address([b'wallet',bytes(mint)],PROGRAM);state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM)
 vm=LiteSVM();vm.add_program(PROGRAM,binary.read_bytes());vm.airdrop(payer.pubkey(),10**10);vm.set_account(wallet,Account(10**9,b'',Pubkey.default()))
 if case.get('wrong_wallet_owner'):vm.set_account(wallet,Account(10**9,b'',token_program))
 for m in [mint,funding]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',1000);md[44]=6;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),token_program))
 sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(payer.pubkey())+bytes(Pubkey.from_bytes(bytes([58])*32) if case.get('wrong_state_mint') else mint)+bytes(Pubkey.from_bytes(bytes([59])*32) if case.get('wrong_state_funding') else funding)+struct.pack('<QBBq',case.get('goal',1000),case.get('closed',1),case.get('started',0),case.get('expiry',-1))+bytes(3)+struct.pack('<H',case.get('carry',1000))+bytes(32)+bytes([case.get('curve',1)])
 vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
 def ta(owner,amount):
  key,_=Pubkey.find_program_address([bytes(owner),bytes(token_program),bytes(funding)],ATA);data=bytearray(165);data[:32]=bytes(funding);data[32:64]=bytes(owner);data[64:72]=struct.pack('<Q',amount);data[108]=1;vm.set_account(key,Account(10**7,bytes(data),token_program));return key
 source=ta(wallet,case.get('balance',2000));dest=ta(payer.pubkey(),0)
 keys=[payer.pubkey(),mint,funding,wallet,source,dest,state,token_program,ATA];metas=[AccountMeta(k,i==0,i in [0,3,4,5,6]) for i,k in enumerate(keys)]
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:init_redemption').digest()[:8],metas);tx=Transaction.new_signed_with_payer([ix],payer.pubkey(),[payer],vm.latest_blockhash());r=json.loads(vm.send_transaction(tx).to_json())
 return {'error':r.get('err'),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:7]},'logs':r.get('meta',r).get('logs')}

def main():
 cases=[{}, {'token_2022':True,'balance':0}, {'wrong_wallet_owner':True,'balance':0},{'wrong_state_mint':True},{'wrong_state_funding':True}, {'balance':1000},{'balance':500},{'balance':0},{'carry':0},{'carry':10000},{'carry':65535},{'curve':0},{'closed':0},{'closed':0,'expiry':0},{'started':1},{'started':1,'closed':0},{'expiry':9999999999},{'balance':2001,'carry':3333}]
 results=[]
 for case in cases:
  a=activate(ROOT/'evidence/mainnet.so',case);b=activate(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print('original',a['error'],a['logs'],'candidate',b['error'],b['logs'])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-init-redemption.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
