"""Local differential token redemption and snapshot tests."""
from differential_burn import *

def redeem(binary,case):
 payer=Keypair.from_seed(bytes([42])*32);mint=Pubkey.from_bytes(bytes([50])*32);redeem_mint=Pubkey.from_bytes(bytes([51])*32);wallet,_=Pubkey.find_program_address([b'wallet',bytes(mint)],PROGRAM)
 vm=LiteSVM();vm.add_program(PROGRAM,binary.read_bytes());vm.airdrop(payer.pubkey(),10**10);vm.set_account(wallet,Account(10**9,b'',Pubkey.default()))
 if case.get('wrong_wallet_owner'):vm.set_account(wallet,Account(10**9,b'',TOKEN))
 if case.get('same_mint'):redeem_mint=mint
 for m in [mint,redeem_mint]:
  md=bytearray(82);md[36:44]=struct.pack('<Q',case.get('supply',1000));md[44]=6;md[45]=1;vm.set_account(m,Account(10**7,bytes(md),TOKEN))
 def ta(owner,amount):
  key,_=Pubkey.find_program_address([bytes(owner),bytes(TOKEN),bytes(redeem_mint)],ATA);data=bytearray(165);data[:32]=bytes(redeem_mint);data[32:64]=bytes(owner);data[64:72]=struct.pack('<Q',amount);data[108]=1;vm.set_account(key,Account(10**7,bytes(data),TOKEN));return key
 source=ta(wallet,case.get('balance',1000000));dest=ta(payer.pubkey(),0)
 user,_=Pubkey.find_program_address([b'user_metadata',bytes(mint),bytes(payer.pubkey())],PROGRAM);vm.set_account(user,Account(1002240,hashlib.sha256(b'account:UserDaoBurned').digest()[:8]+struct.pack('<Q',case.get('burned',100)),PROGRAM))
 snapshot,_=Pubkey.find_program_address([b'token_acc_metadata',bytes(mint),bytes(source)],PROGRAM);redeemed,_=Pubkey.find_program_address([b'token_redeem',bytes(mint),bytes(source),bytes(payer.pubkey())],PROGRAM)
 if case.get('missing_dest'):vm.set_account(dest,Account(0,b'',Pubkey.default()))
 if case.get('non_ata_source'):
  alternative=Pubkey.from_bytes(bytes([62])*32);vm.set_account(alternative,vm.get_account(source));source=alternative
  snapshot,_=Pubkey.find_program_address([b'token_acc_metadata',bytes(mint),bytes(source)],PROGRAM);redeemed,_=Pubkey.find_program_address([b'token_redeem',bytes(mint),bytes(source),bytes(payer.pubkey())],PROGRAM)
 if 'snapshot' in case:vm.set_account(snapshot,Account(1064880,hashlib.sha256(b'account:TokenAccountRedemption').digest()[:8]+bytes([1])+struct.pack('<QQ',case['snapshot'],case.get('distributed',0)),PROGRAM))
 if 'redeemed' in case:vm.set_account(redeemed,Account(1002240,hashlib.sha256(b'account:UserDaoBurnRedeemed').digest()[:8]+struct.pack('<Q',case['redeemed']),PROGRAM))
 keys=[payer.pubkey(),mint,redeem_mint,wallet,source,dest,user,snapshot,redeemed,TOKEN,Pubkey.default(),ATA];metas=[AccountMeta(k,i==0,i in [0,3,4,5,6,7,8]) for i,k in enumerate(keys)]
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:redeem_tokens').digest()[:8]+struct.pack('<Q',case.get('amount',10)),metas);tx=Transaction.new_signed_with_payer([ix],payer.pubkey(),[payer],vm.latest_blockhash());r=json.loads(vm.send_transaction(tx).to_json())
 return {'error':r.get('err'),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:9]},'logs':r.get('meta',r).get('logs')}

def main():
 cases=[{}, {'same_mint':True,'amount':0}, {'wrong_wallet_owner':True,'amount':0}, {'amount':0},{'amount':100},{'amount':101},{'redeemed':99},{'snapshot':1000000,'balance':1500000,'distributed':1},{'supply':0},{'supply':3,'amount':1},{'redeemed':2**64-1},{'snapshot':10**12},{'distributed':2**64-1,'snapshot':1000000},{'missing_dest':True},{'non_ata_source':True}]
 results=[]
 for case in cases:
  a=redeem(ROOT/'evidence/mainnet.so',case);b=redeem(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:print('original',a['error'],a['logs'],'candidate',b['error'],b['logs'])
  results.append({'case':case,'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-tokens.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
