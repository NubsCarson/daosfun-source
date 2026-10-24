"""Exercise escrow-transfer behavior, initialization, constraints and rollback."""
from differential import *
import struct
TOKEN=Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');ATA=Pubkey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')

def burn(binary,case):
 payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM)
 vm=LiteSVM();vm.add_program(PROGRAM,binary.read_bytes());vm.airdrop(payer.pubkey(),10**10)
 md=bytearray(82);md[36:44]=struct.pack('<Q',1000000);md[44]=6;md[45]=1;vm.set_account(mint,Account(10**7,bytes(md),TOKEN))
 sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(payer.pubkey())+bytes(mint)+bytes(Pubkey.default())+struct.pack('<QBBq',0,case.get('closed',0),case.get('redemption',1),-1)+bytes(3)+bytes(2)+bytes(32)+bytes(1)
 if case.get('wrong_state_mint'):sd=sd[:40]+bytes(32)+sd[72:]
 vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
 def ta(owner,amount):
  key,_=Pubkey.find_program_address([bytes(owner),bytes(TOKEN),bytes(mint)],ATA);data=bytearray(165);data[:32]=bytes(mint);data[32:64]=bytes(owner);data[64:72]=struct.pack('<Q',amount);data[108]=1;vm.set_account(key,Account(10**7,bytes(data),TOKEN));return key
 source=ta(payer.pubkey(),1000);dest=ta(state,0)
 user,_=Pubkey.find_program_address([b'user_metadata',bytes(mint),bytes(payer.pubkey())],PROGRAM)
 if case.get('existing') is not None:vm.set_account(user,Account(1002240,hashlib.sha256(b'account:UserDaoBurned').digest()[:8]+struct.pack('<Q',case['existing']),PROGRAM))
 if case.get('missing_dest'):vm.set_account(dest,Account(0,b'',Pubkey.default()))
 if case.get('wrong_source'):
  source=ta(Pubkey.from_bytes(bytes([61])*32),1000)
 keys=[payer.pubkey(),mint,state,source,dest,user,TOKEN,Pubkey.default(),ATA]
 metas=[AccountMeta(k,i==0,i in [0,2,3,4,5]) for i,k in enumerate(keys)]
 if case.get('non_ata'):
  alternative=Pubkey.from_bytes(bytes([63])*32);vm.set_account(alternative,vm.get_account(source));metas[3]=AccountMeta(alternative,False,True)
 if case.get('readonly_state'):metas[2]=AccountMeta(state,False,False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:burn_dao_tokens').digest()[:8]+struct.pack('<Q',case.get('amount',100)),metas)
 tx=Transaction.new_signed_with_payer([ix],payer.pubkey(),[payer],vm.latest_blockhash());r=json.loads(vm.send_transaction(tx).to_json())
 saved={str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:6]}
 return {'error':r.get('err'),'accounts':saved,'logs':r.get('meta',r).get('logs')}

def main():
 cases=[{}, {'wrong_state_mint':True}, {'amount':0},{'amount':1001},{'existing':10},{'existing':2**64-1},{'redemption':0},{'closed':1},{'missing_dest':True},{'wrong_source':True},{'readonly_state':True},{'non_ata':True}]
 results=[]
 for case in cases:
  a=burn(ROOT/'evidence/mainnet.so',case);b=burn(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print('original error',a['error'],a['logs'],'candidate error',b['error'],b['logs'])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-burn.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
