"""Local, signed transaction tests for low-severity redemption edge cases.

No RPC, real keys, or on-chain transactions. Initial DAO state is a post-close,
redemption-open fixture. User redemption credits are created by actual calls to
burn_dao_tokens, not by fabricating user receipt accounts.
"""
from pathlib import Path
import sys, hashlib, struct, json
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from differential import Account, AccountMeta, Instruction, Keypair, LiteSVM, Pubkey, Transaction, PROGRAM
from differential_burn import TOKEN, ATA
from solders.system_program import transfer, TransferParams

ROOT = Path(__file__).resolve().parents[2]
T22 = Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')


def disc(name): return hashlib.sha256(('global:' + name).encode()).digest()[:8]
def receipt(name): return hashlib.sha256(('account:' + name).encode()).digest()[:8]
def pda(*seeds): return Pubkey.find_program_address(list(seeds), PROGRAM)[0]
def amt(vm, key): return struct.unpack_from('<Q', vm.get_account(key).data, 64)[0]

class Fixture:
    def __init__(self, binary, wallet_balance=1_000_000):
        self.vm = LiteSVM().with_transaction_history(0)
        self.vm.add_program(PROGRAM, binary.read_bytes())
        self.vm.add_program(T22, (ROOT/'evidence/token-2022.so').read_bytes())
        self.attacker = Keypair.from_seed(bytes([71])*32)
        self.holder = Keypair.from_seed(bytes([72])*32)
        self.donor = Keypair.from_seed(bytes([73])*32)
        self.mint = Pubkey.from_bytes(bytes([74])*32)
        self.asset = Pubkey.from_bytes(bytes([75])*32)
        self.state = pda(b'state',bytes(self.mint))
        self.wallet = pda(b'wallet',bytes(self.mint))
        for k in [self.attacker,self.holder,self.donor]: self.vm.airdrop(k.pubkey(),10**10)
        for mint, owner, supply in [(self.mint,T22,1000),(self.asset,TOKEN,1_000_000)]:
            d=bytearray(82); d[36:44]=struct.pack('<Q',supply); d[44]=6; d[45]=1
            self.vm.set_account(mint,Account(10**7,bytes(d),owner))
        sd=receipt('State')+bytes(self.holder.pubkey())+bytes(self.mint)+bytes(self.asset)+struct.pack('<QBBq',0,1,1,-1)+bytes(3)+bytes(2)+bytes(32)+bytes([1])
        self.vm.set_account(self.state,Account(10**7,sd.ljust(256,b'\0'),PROGRAM))
        self.vm.set_account(self.wallet,Account(wallet_balance,b'',Pubkey.default()))
        self.dao_accounts={}
        for owner,n in [(self.attacker.pubkey(),0),(self.holder.pubkey(),1000),(self.state,0)]:
            self.dao_accounts[str(owner)]=self.token_account(owner,self.mint,T22,n)
        self.asset_accounts={}
        for owner,n in [(self.attacker.pubkey(),0),(self.holder.pubkey(),0),(self.donor.pubkey(),1_000_000),(self.wallet,0)]:
            self.asset_accounts[str(owner)]=self.token_account(owner,self.asset,TOKEN,n)
    def token_account(self, owner,mint,program,n):
        key=Pubkey.find_program_address([bytes(owner),bytes(program),bytes(mint)],ATA)[0]
        d=bytearray(165);d[:32]=bytes(mint);d[32:64]=bytes(owner);d[64:72]=struct.pack('<Q',n);d[108]=1
        self.vm.set_account(key,Account(10**7,bytes(d),program));return key
    def send(self,key,ix):
        tx=Transaction.new_signed_with_payer([ix],key.pubkey(),[key],self.vm.latest_blockhash())
        r=json.loads(self.vm.send_transaction(tx).to_json())
        return {'error':r.get('err'),'logs':r.get('meta',r).get('logs')}
    def user(self,key):return pda(b'user_metadata',bytes(self.mint),bytes(key.pubkey()))
    def burn(self,key,n):
        keys=[key.pubkey(),self.mint,self.state,self.dao_accounts[str(key.pubkey())],self.dao_accounts[str(self.state)],self.user(key),T22,Pubkey.default(),ATA]
        return self.send(key,Instruction(PROGRAM,disc('burn_dao_tokens')+struct.pack('<Q',n),[AccountMeta(k,i==0,i in [0,2,3,4,5]) for i,k in enumerate(keys)]))
    def redeem_tokens(self,key,n):
        source=self.asset_accounts[str(self.wallet)]
        snap=pda(b'token_acc_metadata',bytes(self.mint),bytes(source))
        used=pda(b'token_redeem',bytes(self.mint),bytes(source),bytes(key.pubkey()))
        keys=[key.pubkey(),self.mint,self.asset,self.wallet,source,self.asset_accounts[str(key.pubkey())],self.user(key),snap,used,TOKEN,Pubkey.default(),ATA]
        result=self.send(key,Instruction(PROGRAM,disc('redeem_tokens')+struct.pack('<Q',n),[AccountMeta(k,i==0,i in [0,3,4,5,6,7,8]) for i,k in enumerate(keys)]))
        return result,snap,used
    def redeem_sol(self,key,n):
        snap=pda(b'sol_redeem',bytes(self.mint));used=pda(b'user_sol_redeem',bytes(self.mint),bytes(key.pubkey()))
        keys=[key.pubkey(),self.mint,self.wallet,self.user(key),snap,used,Pubkey.default()]
        result=self.send(key,Instruction(PROGRAM,disc('redeem_sol')+struct.pack('<Q',n),[AccountMeta(k,i==0,i in [0,2,3,4,5]) for i,k in enumerate(keys)]))
        return result,snap,used
    def deposit_tokens(self):
        keys=[self.asset_accounts[str(self.donor.pubkey())],self.asset,self.asset_accounts[str(self.wallet)],self.donor.pubkey()]
        return self.send(self.donor,Instruction(TOKEN,bytes([12])+struct.pack('<Q',1_000_000)+bytes([6]),[AccountMeta(k,i==3,i in [0,2]) for i,k in enumerate(keys)]))


def snapshot_case(binary,grief):
    f=Fixture(binary)
    zero=f.burn(f.attacker,0);assert zero['error'] is None,zero
    if grief:
        tr,snap,_=f.redeem_tokens(f.attacker,0);sr,_,_=f.redeem_sol(f.attacker,0)
        assert tr['error'] is None and sr['error'] is None,(tr,sr)
    dep=f.deposit_tokens();assert dep['error'] is None,dep
    soldep=f.send(f.donor,transfer(TransferParams(from_pubkey=f.donor.pubkey(),to_pubkey=f.wallet,lamports=1_000_000_000)));assert soldep['error'] is None
    burn=f.burn(f.holder,1000);assert burn['error'] is None,burn
    tr,snap,used=f.redeem_tokens(f.holder,1000);sr,_,_=f.redeem_sol(f.holder,1000)
    assert tr['error'] is None and sr['error'] is None,(tr,sr)
    repeat,_,_=f.redeem_tokens(f.holder,1);assert repeat['error'] is not None
    return dict(zero_holder_credit=struct.unpack_from('<Q',f.vm.get_account(f.user(f.attacker)).data,8)[0],
      holder_tokens_received=amt(f.vm,f.asset_accounts[str(f.holder.pubkey())]),
      treasury_tokens_remaining=amt(f.vm,f.asset_accounts[str(f.wallet)]),
      treasury_lamports_remaining=f.vm.get_account(f.wallet).lamports if f.vm.get_account(f.wallet) else 0,
      snapshot_tokens=struct.unpack_from('<Q',f.vm.get_account(snap).data,9)[0],
      holder_credit_consumed=struct.unpack_from('<Q',f.vm.get_account(used).data,8)[0],
      duplicate_claim_error=repeat['error'])


def rent_case(binary):
    f=Fixture(binary,wallet_balance=900_000)
    assert f.burn(f.holder,1000)['error'] is None
    result,_,used=f.redeem_sol(f.holder,100)
    assert result['error'] is None,result
    remaining=f.vm.get_account(f.wallet).lamports
    credit=struct.unpack_from('<Q',f.vm.get_account(used).data,8)[0]
    full,_,_=f.redeem_sol(f.holder,900);assert full['error'] is None,full
    return dict(partial_claim_error=result['error'],partial_claim_logs=result['logs'],
      wallet_balance_before=900000,partial_payout=90000,remaining_after_partial=remaining,
      reported_rent_exemption_minimum=f.vm.get_rent().minimum_balance(0),
      credited_partial_claim=credit,remaining_claim_error=full['error'],
      full_claim_remaining=f.vm.get_account(f.wallet).lamports if f.vm.get_account(f.wallet) else 0)


def main():
    results={}
    for label,binary in [('original',ROOT/'evidence/mainnet.so'),('rebuilt',ROOT/'binaries/dao_v1.deployed.so')]:
        grief=snapshot_case(binary,True);control=snapshot_case(binary,False);rent=rent_case(binary)
        assert grief['holder_tokens_received']==0 and grief['treasury_tokens_remaining']==1_000_000 and grief['treasury_lamports_remaining']==1_000_000_000
        assert control['holder_tokens_received']==1_000_000 and control['treasury_tokens_remaining']==0 and control['treasury_lamports_remaining']==0
        results[label]=dict(sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),zero_snapshot_grief=grief,no_early_snapshot_control=control,rent_remainder=rent)
    assert results['original']==results['rebuilt']
    out=ROOT/'audit/results/second-redemption.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
