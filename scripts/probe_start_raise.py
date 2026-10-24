"""Local exploration of fundraising CPI; no chain transactions."""
from differential_burn import *
T22=Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')
FR=Pubkey.from_string('ETK5PUmiqVDRsd1TPFqCu84bsrLNG4YySZND96PEjW97')
def probe(duration=604801,case=None,binary=None,verbose=True):
 case=case or {}
 payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);funding=Pubkey.from_bytes(bytes([51])*32);state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,(binary or ROOT/'evidence/mainnet.so').read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.airdrop(payer.pubkey(),10**10)
 vm.add_program(FR,(ROOT/'evidence/fundraise.so').read_bytes())
 for m,tp in [(mint,T22),(funding,TOKEN)]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',10**18);md[44]=9;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),tp))
 sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(payer.pubkey())+bytes(mint)+bytes(funding)+struct.pack('<QBBq',case.get('goal',1000000000),case.get('closed',0),case.get('started',0),9999999999)+bytes(3)+struct.pack('<H',1000)+bytes(33)
 if case.get('curve'):sd=sd[:-1]+bytes([1])
 vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
 def ta(owner,m,tp,amount):
  k,_=Pubkey.find_program_address([bytes(owner),bytes(tp),bytes(m)],ATA);d=bytearray(165);d[:32]=bytes(m);d[32:64]=bytes(owner);d[64:72]=struct.pack('<Q',amount);d[108]=1;vm.set_account(k,Account(10**7,bytes(d),tp));return k
 vault=ta(state,mint,T22,10**18);admintoken=ta(payer.pubkey(),mint,T22,0);adminfund=ta(payer.pubkey(),funding,TOKEN,10**10)
 frstate,_=Pubkey.find_program_address([b'fundraise',bytes(state),bytes(mint)],FR);frtoken,_=Pubkey.find_program_address([bytes(frstate),bytes(T22),bytes(mint)],ATA);frfund,_=Pubkey.find_program_address([bytes(frstate),bytes(TOKEN),bytes(funding)],ATA)
 ta(frstate,funding,TOKEN,0)
 if case.get('wrong_admin'):
  bad=bytearray(sd);bad[8:40]=bytes(32);vm.set_account(state,Account(10**7,bytes(bad).ljust(256,b'\0'),PROGRAM))
 if case.get('missing_admin_token'):vm.set_account(admintoken,Account(0,b'',Pubkey.default()))
 if case.get('missing_admin_fund'):vm.set_account(adminfund,Account(0,b'',Pubkey.default()))
 if 'state_byte' in case:
  bad=bytearray(sd);bad[case['state_byte']]=255;vm.set_account(state,Account(10**7,bytes(bad).ljust(256,b'\0'),PROGRAM))
 keys=[payer.pubkey(),mint,funding,state,vault,frstate,frtoken,PROGRAM,admintoken,adminfund,frfund,T22,TOKEN,Pubkey.default(),ATA,FR]
 if case.get('funding_token_2022'):keys[12]=T22
 if case.get('dao_token_legacy'):keys[11]=TOKEN
 if 'whitelist_signer' in case:
  keys[7]=Pubkey.from_bytes(bytes([92])*32);vm.set_account(keys[7],Account(10**7,b'',Pubkey.default()))
 if 'alternate' in case:
  i=case['alternate'];new=Pubkey.from_bytes(bytes([70+i])*32);old=vm.get_account(keys[i]);
  if old:vm.set_account(new,old)
  keys[i]=new
 metas=[AccountMeta(k,i==0,i not in [1,2,7,11,12,13,14,15]) for i,k in enumerate(keys)]
 if 'whitelist_signer' in case:metas[7]=AccountMeta(keys[7],case['whitelist_signer'],False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:start_raise').digest()[:8]+struct.pack('<I',duration),metas)
 if case.get('readonly_state'):metas[3]=AccountMeta(state,False,False)
 if 'readonly' in case:
  i=case['readonly'];metas[i]=AccountMeta(keys[i],i==0,False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:start_raise').digest()[:8]+struct.pack('<I',duration),metas)
 r=json.loads(vm.send_transaction(Transaction.new_unsigned(Message.new_with_blockhash([ix],payer.pubkey(),vm.latest_blockhash()))).to_json());(ROOT/'evidence/start-raise-probe.json').write_text(json.dumps(r,indent=2))
 if verbose:print(r.get('err'),r.get('meta',r).get('logs'))
 return {'error':r.get('err'),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:11] if k != PROGRAM},'logs':r.get('meta',r).get('logs')}
if __name__=='__main__':probe()
