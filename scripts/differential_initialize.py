"""Differential token-2022 initialization with deployed dependency binary."""
from differential_burn import *
from solders.compute_budget import set_compute_unit_limit
from solders.rent import Rent

def initialize(binary,case):
 TOKEN2022=Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')
 payer=Keypair.from_seed(bytes([42])*32);mintkey=Keypair.from_seed(bytes([50])*32);mint=mintkey.pubkey();state,_=Pubkey.find_program_address([b'state',bytes(mint)],PROGRAM);vault,_=Pubkey.find_program_address([bytes(state),bytes(TOKEN2022),bytes(mint)],ATA)
 funding=Pubkey.from_string('So11111111111111111111111111111111111111112');fee_program=Pubkey.from_string('Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk');fee_share,_=Pubkey.find_program_address([b'fee_share_state',bytes(mint)],fee_program)
 vm=LiteSVM().with_sigverify(False).with_transaction_history(0)
 if 'rent_lamports' in case:vm.set_rent(Rent(case['rent_lamports'],2.0,50))
 vm.add_program(PROGRAM,binary.read_bytes());vm.airdrop(payer.pubkey(),10**10);vm.add_program(TOKEN2022,(ROOT/'evidence/token-2022.so').read_bytes())
 md=bytearray(82);md[36:44]=struct.pack('<Q',1000000);md[44]=9;md[45]=1;vm.set_account(funding,Account(10**7,bytes(md),TOKEN))
 fee=bytearray(base64.b64decode(json.loads((ROOT/'evidence/fee-authority-sample.json').read_text())['value']['data'][0]));fee[48:80]=bytes(mint);fee[80:112]=bytes(payer.pubkey());
 if case.get('wrong_creator'):fee[80:112]=bytes(32)
 if case.get('wrong_mint'):fee[48:80]=bytes(32)
 if case.get('wrong_funding'):fee[16:48]=bytes(32)
 if case.get('bad_disc'):fee[:8]=bytes(8)
 if case.get('tail_ff'):fee[168]=255
 if 'fee_byte' in case:fee[case['fee_byte'][0]]=case['fee_byte'][1]
 if 'fee_len' in case:fee=fee[:case['fee_len']]
 vm.set_account(fee_share,Account(10**7,bytes(fee),fee_program))
 carry=case.get('carry');args=b''.join(struct.pack('<I',len(x))+x for x in [case.get('name',b'Recovered'),b'RCV',b'uri'])+struct.pack('<IQ',case.get('duration',31536000),case.get('goal',1000000000))+(bytes([0]) if carry is None else bytes([1])+struct.pack('<H',carry))
 wallet,_=Pubkey.find_program_address([b'wallet',bytes(mint)],PROGRAM)
 if case.get('wrong_wallet_owner'):vm.set_account(wallet,Account(10**7,b'',TOKEN))
 keys=[payer.pubkey(),state,wallet,mint,funding,vault,fee_share,TOKEN2022,ATA,Pubkey.default()]
 metas=[AccountMeta(k,i in [0,3],i in [0,1,2,3,5] and not (i == 2 and case.get('readonly_wallet'))) for i,k in enumerate(keys)]
 ix=Instruction(PROGRAM,hashlib.sha256(b'global:initialize').digest()[:8]+args,metas)
 tx=Transaction.new_unsigned(Message.new_with_blockhash([set_compute_unit_limit(1400000),ix],payer.pubkey(),vm.latest_blockhash()))
 r=json.loads(vm.send_transaction(tx).to_json())
 return {'error':r.get('err'),'accounts':{str(k):vm.get_account(k).to_json() if vm.get_account(k) else None for k in keys[:7]},'logs':r.get('meta',r).get('logs')}

def main():
 cases=[{'rent_lamports':6960},{'wrong_wallet_owner':True},{'readonly_wallet':True},{'carry':4000},{'carry':4001},{'fee_len':137},{'fee_len':136},{'fee_byte':[112,255]},{'fee_byte':[112,1]},{'tail_ff':True},{}, {'carry':0},{'carry':10000},{'carry':10001},{'carry':65535},{'name':b''},{'duration':0},{'duration':2**32-1},{'goal':0},{'wrong_creator':True},{'wrong_mint':True},{'wrong_funding':True},{'bad_disc':True}]
 results=[]
 for case in cases:
  a=initialize(ROOT/'evidence/mainnet.so',case);b=initialize(ROOT/'target/deploy/dao_v1_recovered.so',case);same=all(a[k]==b[k] for k in ['error','accounts']);print(case,'PASS' if same else 'FAIL')
  if not same:
   print('original error',a['error'],'candidate error',b['error'])
   print('different accounts',[k for k in a['accounts'] if a['accounts'][k]!=b['accounts'][k]])
  results.append({'case':{k:v.decode() if isinstance(v,bytes) else v for k,v in case.items()},'matches':same,'original':a,'candidate':b})
 (ROOT/'evidence/differential-initialize.json').write_text(json.dumps(results,indent=2));assert all(r['matches'] for r in results)
if __name__=='__main__':main()
