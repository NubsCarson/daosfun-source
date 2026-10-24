"""Reproduce direct bonding-pool initialization locally."""
from probe_claim_dbc import *
from solders.compute_budget import set_compute_unit_limit

def initialize_bonding(binary=None,case=None):
 case=case or {};payer=Keypair.from_seed(bytes([42])*32);mintkey=Keypair.from_seed(bytes([50])*32);mint=mintkey.pubkey();funding=Pubkey.from_string('So11111111111111111111111111111111111111112');ma,_=Pubkey.find_program_address([b'meteora_authority'],PROGRAM);pa,_=Pubkey.find_program_address([b'pool_authority'],DBC);ea,_=Pubkey.find_program_address([b'__event_authority'],DBC);config=Pubkey.from_string('BkoMF8PzYwoVQTKcQ6uNeQrHytw1jJN6ig4JzjcKS3iF');state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM)
 pool,_=Pubkey.find_program_address([b'pool',bytes(config),max(bytes(mint),bytes(funding)),min(bytes(mint),bytes(funding))],DBC);fee,_=Pubkey.find_program_address([b'fee_share_state',bytes(mint)],FEE);basevault,_=Pubkey.find_program_address([b'token_vault',bytes(mint),bytes(pool)],DBC);quotevault,_=Pubkey.find_program_address([b'token_vault',bytes(funding),bytes(pool)],DBC)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,(binary or ROOT/'evidence/mainnet.so').read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.add_program(DBC,(ROOT/'evidence/meteora-dbc.so').read_bytes());vm.airdrop(payer.pubkey(),10**10)
 md=bytearray(82);md[36:44]=struct.pack('<Q',1000000000);md[44]=9;md[45]=1;vm.set_account(funding,Account(10**7,bytes(md),TOKEN))
 cd=json.loads((ROOT/'evidence/dbc-config.json').read_text())['value'];vm.set_account(config,Account(cd['lamports'],base64.b64decode(cd['data'][0]),DBC))
 fd=bytearray(169);fd[:8]=hashlib.sha256(b'account:FeeShareState').digest()[:8];fd[16:48]=bytes(funding);fd[48:80]=bytes(mint);fd[80:112]=bytes(payer.pubkey());vm.set_account(fee,Account(10**7,bytes(fd),FEE))
 keys=[payer.pubkey(),mint,funding,state,fee,config,pool,basevault,quotevault,ma,pa,ea,TOKEN,T22,ATA,Pubkey.default(),DBC]
 if 'byte' in case:
  i,offset,value=case['byte'];a=vm.get_account(keys[i]);d=bytearray(a.data);d[offset]=value;vm.set_account(keys[i],Account(a.lamports,bytes(d),a.owner))
 if 'alternate' in case:
  i=case['alternate'];k=Pubkey.from_bytes(bytes([80+i])*32);a=vm.get_account(keys[i]);
  if a:vm.set_account(k,a)
  keys[i]=k
 metas=[AccountMeta(k,i in [0,1],i in [0,1,3,6,7,8,9]) for i,k in enumerate(keys)]
 if 'readonly' in case:
  i=case['readonly'];metas[i]=AccountMeta(keys[i],i in [0,1],False)
 args=b''.join(struct.pack('<I',len(x))+x for x in [case.get('name','Recovered').encode(),b'RCV',b'uri'])
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:init_bonding_on_meteora').digest()[:8]+args,metas);msg=Message.new_with_blockhash([set_compute_unit_limit(1400000),ix],payer.pubkey(),vm.latest_blockhash());r=json.loads(vm.send_transaction(Transaction.new_unsigned(msg)).to_json());return {'error':r.get('err'),'logs':r.get('meta',r).get('logs'),'raw':r,'keys':list(map(str,msg.account_keys)),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:10]}}
if __name__=='__main__':
 r=initialize_bonding();print(r['error'],r['logs']);(ROOT/'evidence/bonding-init-probe.json').write_text(json.dumps(r,indent=2))
