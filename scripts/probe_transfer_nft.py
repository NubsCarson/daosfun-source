"""Synthetic local fixtures for the position-NFT ownership change."""
from differential_burn import *
T22=Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb');AMM=Pubkey.from_string('cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG');FEE=Pubkey.from_string('Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk')
def probe(binary=None,case=None):
 case=case or {};payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);funding=Pubkey.from_bytes(bytes([51])*32);state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM);ma,_=Pubkey.find_program_address([b'meteora_authority'],PROGRAM)
 pool=Pubkey.from_bytes(bytes([52])*32);nftmint,_=Pubkey.find_program_address([b'position_nft_mint',bytes(mint)],PROGRAM);nftacc,_=Pubkey.find_program_address([b'position_nft_account',bytes(nftmint)],AMM);position,_=Pubkey.find_program_address([b'position',bytes(nftmint)],AMM);fee,_=Pubkey.find_program_address([b'fee_share_state',bytes(mint)],FEE)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,(binary or ROOT/'evidence/mainnet.so').read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.airdrop(payer.pubkey(),10**10)
 for m,tp in [(mint,T22),(funding,TOKEN),(nftmint,T22)]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',1);md[44]=9;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),tp))
 sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(payer.pubkey())+bytes(mint)+bytes(funding)+struct.pack('<QBBq',1000000000,0,0,9999999999)+bytes(3)+struct.pack('<H',1000)+bytes(fee)+bytes([1]);vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
 pd=bytearray(1112);pd[:8]=hashlib.sha256(b'account:Pool').digest()[:8];pd[168:200]=bytes(mint);pd[200:232]=bytes(funding);vm.set_account(pool,Account(10**7,bytes(pd),AMM))
 pd=bytearray(408);pd[:8]=hashlib.sha256(b'account:Position').digest()[:8];pd[8:40]=bytes(pool);pd[40:72]=bytes(nftmint);vm.set_account(position,Account(10**7,bytes(pd),AMM))
 td=bytearray(165);td[:32]=bytes(nftmint);td[32:64]=bytes(ma);td[64:72]=struct.pack('<Q',1);td[108]=1;vm.set_account(nftacc,Account(10**7,bytes(td),T22))
 fd=bytearray(169);fd[:8]=hashlib.sha256(b'account:FeeShareState').digest()[:8];fd[16:48]=bytes(funding);fd[48:80]=bytes(mint);fd[80:112]=bytes(payer.pubkey());vm.set_account(fee,Account(10**7,bytes(fd),FEE))
 keys=[payer.pubkey(),mint,funding,state,pool,nftmint,nftacc,position,ma,fee,T22]
 if 'byte' in case:
  i,offset,value=case['byte'];a=vm.get_account(keys[i]);d=bytearray(a.data);d[offset]=value;vm.set_account(keys[i],Account(a.lamports,bytes(d),a.owner))
 if 'alternate' in case:
  i=case['alternate'];k=Pubkey.from_bytes(bytes([80+i])*32);a=vm.get_account(keys[i]);
  if a:vm.set_account(k,a)
  keys[i]=k
 metas=[AccountMeta(k,i==0,i in [0,6,7]) for i,k in enumerate(keys)]
 if 'readonly' in case:
  i=case['readonly'];metas[i]=AccountMeta(keys[i],i==0,False)
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:transfer_position_nft_to_fee_share').digest()[:8],metas)
 r=json.loads(vm.send_transaction(Transaction.new_unsigned(Message.new_with_blockhash([ix],payer.pubkey(),vm.latest_blockhash()))).to_json());return {'error':r.get('err'),'logs':r.get('meta',r).get('logs'),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:10]}}
if __name__=='__main__':
 r=probe();print(r['error'],r['logs'])
