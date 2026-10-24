"""Local fee-claim fixture with the real deployed DBC dependency."""
from probe_transfer_nft import *
DBC=Pubkey.from_string('dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN')
def claim(binary=None,case=None):
 case=case or {};payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);funding=Pubkey.from_bytes(bytes([51])*32);ma,_=Pubkey.find_program_address([b'meteora_authority'],PROGRAM);pa,_=Pubkey.find_program_address([b'pool_authority'],DBC);ea,_=Pubkey.find_program_address([b'__event_authority'],DBC);config=Pubkey.from_string('BkoMF8PzYwoVQTKcQ6uNeQrHytw1jJN6ig4JzjcKS3iF')
 pool,_=Pubkey.find_program_address([b'pool',bytes(config),max(bytes(mint),bytes(funding)),min(bytes(mint),bytes(funding))],DBC);fee,_=Pubkey.find_program_address([b'fee_share_state',bytes(mint)],FEE)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,(binary or ROOT/'evidence/mainnet.so').read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.add_program(DBC,(ROOT/'evidence/meteora-dbc.so').read_bytes());vm.airdrop(payer.pubkey(),10**10)
 for m,tp in [(mint,T22),(funding,TOKEN)]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',1000000000);md[44]=9;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),tp))
 def ta(owner,m,tp,amount,key=None):
  k=key or Pubkey.find_program_address([bytes(owner),bytes(tp),bytes(m)],ATA)[0];d=bytearray(165);d[:32]=bytes(m);d[32:64]=bytes(owner);d[64:72]=struct.pack('<Q',amount);d[108]=1;vm.set_account(k,Account(10**7,bytes(d),tp));return k
 basevault=ta(pa,mint,T22,10000,Pubkey.find_program_address([b'token_vault',bytes(mint),bytes(pool)],DBC)[0]);quotevault=ta(pa,funding,TOKEN,10000,Pubkey.find_program_address([b'token_vault',bytes(funding),bytes(pool)],DBC)[0]);matoken=ta(ma,mint,T22,500);mafund=ta(ma,funding,TOKEN,700);feetoken=ta(fee,mint,T22,100);feefund=ta(fee,funding,TOKEN,200)
 cd=bytearray(1048);cd[:8]=hashlib.sha256(b'account:PoolConfig').digest()[:8];cd[8:40]=bytes(funding);cd[40:72]=bytes(ma);vm.set_account(config,Account(10**7,bytes(cd),DBC))
 pd=bytearray(424);pd[:8]=hashlib.sha256(b'account:VirtualPool').digest()[:8];pd[72:104]=bytes(config);pd[104:136]=bytes(ma);pd[136:168]=bytes(mint);pd[168:200]=bytes(basevault);pd[200:232]=bytes(quotevault);pd[264:272]=struct.pack('<Q',case.get('base_fee',123));pd[272:280]=struct.pack('<Q',case.get('quote_fee',456));vm.set_account(pool,Account(10**7,bytes(pd),DBC))
 fd=bytearray(169);fd[:8]=hashlib.sha256(b'account:FeeShareState').digest()[:8];fd[16:48]=bytes(funding);fd[48:80]=bytes(mint);fd[80:112]=bytes(payer.pubkey());vm.set_account(fee,Account(10**7,bytes(fd),FEE))
 keys=[fee,mint,funding,config,pool,quotevault,basevault,ma,mafund,matoken,feefund,feetoken,pa,ea,T22,TOKEN,ATA,DBC]
 if 'byte' in case:
  i,offset,value=case['byte'];a=vm.get_account(keys[i]);d=bytearray(a.data);d[offset]=value;vm.set_account(keys[i],Account(a.lamports,bytes(d),a.owner))
 if 'alternate' in case:
  i=case['alternate'];k=Pubkey.from_bytes(bytes([80+i])*32);a=vm.get_account(keys[i]);
  if a:vm.set_account(k,a)
  keys[i]=k
 metas=[AccountMeta(k,i==0,i in [0,4,5,6,8,9,10,11]) for i,k in enumerate(keys)]
 if case.get('unsigned_fee'):metas[0]=AccountMeta(keys[0],False,True)
 if 'readonly' in case:
  i=case['readonly'];metas[i]=AccountMeta(keys[i],i==0,False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:claim_dbc_trading_fees').digest()[:8],metas);msg=Message.new_with_blockhash([ix],payer.pubkey(),vm.latest_blockhash());r=json.loads(vm.send_transaction(Transaction.new_unsigned(msg)).to_json());return {'error':r.get('err'),'logs':r.get('meta',r).get('logs'),'raw':r,'keys':list(map(str,msg.account_keys)),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:12]}}
if __name__=='__main__':
 r=claim();print(r['error'],r['logs']);(ROOT/'evidence/claim-dbc-probe.json').write_text(json.dumps(r,indent=2))
