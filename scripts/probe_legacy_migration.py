"""Explore pool initialization against the original binary in local LiteSVM."""
from probe_start_raise import *
from solders.compute_budget import set_compute_unit_limit
AMM=Pubkey.from_string('cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG')
HEDGE=Pubkey.from_string('HedgENAip7ZEzRj6T3ZbY1PmDFXU5XKx1BFSKbxvVD7V')
FEE=Pubkey.from_string('Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk')
def migrate(binary=None,case=None):
 case=case or {};payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);funding=Pubkey.from_bytes(bytes([51])*32)
 pda=lambda seeds,program=PROGRAM:Pubkey.find_program_address(seeds,program)[0]
 state=pda([b'state',bytes(mint)]);wallet=pda([b'wallet',bytes(mint)]);ma=pda([b'meteora_authority']);fee=pda([b'fee_share_state',bytes(mint)],FEE)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,(binary or ROOT/'evidence/mainnet.so').read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.add_program(AMM,(ROOT/('evidence/meteora-damm-v2-0.1.3.so' if case.get('historical') else 'evidence/meteora-damm-v2.so')).read_bytes());vm.add_program(HEDGE,(ROOT/'evidence/hedgefun.so').read_bytes());vm.airdrop(payer.pubkey(),10**11)
 for m,tp in [(mint,T22),(funding,TOKEN)]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',10**18);md[44]=9;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),tp))
 sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(payer.pubkey())+bytes(mint)+bytes(funding)+struct.pack('<QBBq',10**9,0,0,9999999999)+bytes(3)+struct.pack('<H',1000)+bytes(fee)+bytes(1)
 vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
 def ta(owner,m,tp,amount):
  k=pda([bytes(owner),bytes(tp),bytes(m)],ATA);d=bytearray(165);d[:32]=bytes(m);d[32:64]=bytes(owner);d[64:72]=struct.pack('<Q',amount);d[108]=1;vm.set_account(k,Account(10**7,bytes(d),tp));return k
 wf=ta(wallet,funding,TOKEN,0);sf=ta(pda([b'curve',bytes(state)],HEDGE),funding,TOKEN,100*10**9);pf=ta(payer.pubkey(),funding,TOKEN,10**10);st=ta(state,mint,T22,10**18);pt=ta(payer.pubkey(),mint,T22,0)
 fr=pda([b'curve',bytes(state)],HEDGE);fd=hashlib.sha256(b'account:FundraiseState').digest()[:8]+bytes(state)+bytes(mint)+bytes(funding)+struct.pack('<QQqQBB',850*10**15,10**9,1,10**9,1,1)+bytes(state)+bytes(1);vm.set_account(fr,Account(10**7,fd.ljust(204,b'\0'),FR))
 fee_data=hashlib.sha256(b'account:FeeShareState').digest()[:8]+bytes(8)+bytes(funding)+bytes(mint)+bytes(payer.pubkey())+bytes(57);vm.set_account(fee,Account(10**7,fee_data,FEE))
 config=Pubkey.from_string('CtnY6H6AYJJ3WxN5MSY2NQAqrzPY4qTW1gb5ySzvPhaE');pa=pda([b'pool_authority'],AMM);pool=pda([b'pool',bytes(config),max(bytes(mint),bytes(funding)),min(bytes(mint),bytes(funding))],AMM);nft=pda([b'position_nft_mint',bytes(mint)]);nfta=pda([b'position_nft_account',bytes(nft)],AMM);position=pda([b'position',bytes(nft)],AMM);ea=pda([b'__event_authority'],AMM)
 bv=pda([b'token_vault',bytes(mint),bytes(pool)],AMM);qv=pda([b'token_vault',bytes(funding),bytes(pool)],AMM);fnft=pda([b'fee_nft_mint',bytes(mint)]);fna=pda([bytes(fee),bytes(T22),bytes(nft)],ATA)
 sample=next(a for a in json.loads((ROOT/'evidence/hedgefun-samples.json').read_text())['result']['value'] if a);hd=bytearray(base64.b64decode(sample['data'][0]));hd[121]=0;hd[48:80]=bytes(mint);hd[80:112]=bytes(funding);vm.set_account(fr,Account(10**7,bytes(hd),HEDGE))
 keys=[payer.pubkey(),funding,mint,state,fr,sf,wallet,wf,pt,pf,st,bv,qv,fee,fna,ma,config,pa,pool,nft,nfta,position,ea,HEDGE,T22,T22,TOKEN,ATA,Pubkey.default(),Pubkey.from_string('SysvarRent111111111111111111111111111111111'),AMM]
 cd=json.loads((ROOT/'evidence/damm-config.json').read_text())['value'];vm.set_account(config,Account(cd['lamports'],base64.b64decode(cd['data'][0]),AMM))
 if 'qword' in case:
  i,offset,value=case['qword'];old=vm.get_account(keys[i]);d=bytearray(old.data);d[offset:offset+8]=struct.pack('<Q',value);vm.set_account(keys[i],Account(old.lamports,bytes(d),old.owner))
 if 'truncate' in case:
  old=vm.get_account(fr);vm.set_account(fr,Account(old.lamports,old.data[:case['truncate']],old.owner))
 if 'byte' in case:
  i,offset,value=case['byte'];a=vm.get_account(keys[i]);d=bytearray(a.data);d[offset]=value;vm.set_account(keys[i],Account(a.lamports,bytes(d),a.owner))
 if 'alternate' in case:
  i=case['alternate'];k=Pubkey.from_bytes(bytes([80+i])*32);a=vm.get_account(keys[i]);
  if a:vm.set_account(k,a)
  keys[i]=k
 metas=[AccountMeta(k,i==0,True) for i,k in enumerate(keys)]
 if 'readonly' in case:
  i=case['readonly'];metas[i]=AccountMeta(keys[i],i==0,False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:migrate_bonding_to_meteora').digest()[:8],metas)
 msg=Message.new_with_blockhash([set_compute_unit_limit(1400000),ix],payer.pubkey(),vm.latest_blockhash());r=json.loads(vm.send_transaction(Transaction.new_unsigned(msg)).to_json())
 return {'message_keys':list(map(str,msg.account_keys)),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:24]},'raw':r,'error':r.get('err'),'logs':r.get('meta',r).get('logs'),'keys':list(map(str,keys))}
if __name__=='__main__':
 r=migrate();print(r['error']);print('\n'.join(r['logs'] or []));(ROOT/'evidence/legacy-migration-probe.json').write_text(json.dumps(r,indent=2))
