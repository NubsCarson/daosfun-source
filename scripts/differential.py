"""Compare reconstructed handlers against deployed bytecode, entirely in LiteSVM.

Signature cryptography is disabled so public captured accounts can be exercised.
Signer flags and program authorization checks still execute in the VM.
"""
import base64
import hashlib
import json
from pathlib import Path
from solders.account import Account
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = Pubkey.from_string('4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM')
CLOSE_AUTHORITY = Pubkey.from_string('6ZNfAtWS1C1aPQkrgyPrkWmXuFgnNRTSNYjyxgu5yU7D')

def run(binary, scenario, wrong_state_mint=False):
    accounts = json.loads((ROOT/'evidence/full-account-samples.json').read_text())['accounts']
    accounts.update(json.loads((ROOT/'evidence/related-accounts.json').read_text()))
    key, account = next((k, a) for k, a in accounts.items() if a and a['space'] == 256)
    original = base64.b64decode(account['data'][0])
    state = Pubkey.from_string(key)
    admin, mint = Pubkey.from_bytes(original[8:40]), Pubkey.from_bytes(original[40:72])
    vm = LiteSVM().with_sigverify(False).with_transaction_history(0)
    vm.add_program(PROGRAM, binary.read_bytes())
    for k, a in accounts.items():
        if a:
            vm.set_account(Pubkey.from_string(k), Account(a['lamports'], base64.b64decode(a['data'][0]),
                Pubkey.from_string(a['owner']), a['executable'], a['rentEpoch']))
    if wrong_state_mint:
        loaded = vm.get_account(state)
        data = bytearray(loaded.data)
        data[40:72] = bytes([99]) * 32
        vm.set_account(state, Account(loaded.lamports, bytes(data), loaded.owner,
                                      loaded.executable, loaded.rent_epoch))
    payer = Keypair.from_seed(bytes([42])*32)
    vm.airdrop(payer.pubkey(), 10**10)
    vm.set_account(CLOSE_AUTHORITY, Account(10**8, b'', Pubkey.default()))
    outcomes = []
    for index, (name, argument, signer_kind, signer_flag, writable) in enumerate(scenario):
        signer = {'admin': admin, 'global': CLOSE_AUTHORITY, 'outsider': payer.pubkey()}[signer_kind]
        data = hashlib.sha256(('global:'+name).encode()).digest()[:8] + argument
        # Distinguish fixture instruction data; transaction history is disabled because signatures are synthetic.
        data += bytes([index])
        ix = Instruction(PROGRAM, data, [AccountMeta(signer, signer_flag, writable),
            AccountMeta(mint, False, False), AccountMeta(state, False, True)])
        tx = Transaction.new_unsigned(Message.new_with_blockhash([ix], payer.pubkey(), vm.latest_blockhash()))
        outcome = json.loads(vm.send_transaction(tx).to_json())
        outcomes.append({'error': outcome.get('err'), 'state': vm.get_account(state).data.hex(),
                         'logs': outcome.get('meta', outcome).get('logs')})
    return outcomes

def main():
    def step(name, value=b'', signer='admin', flag=True, writable=True):
        return (name, value, signer, flag, writable)
    add, revoke = 'add_delegate_authority', 'revoke_delegate_authority'
    a, b, c, d = (bytes([i])*32 for i in [55, 56, 57, 58])
    scenarios = {
        'wrong_state_mint_unauthorized_add': [step(add, a, 'outsider')],
        'wrong_state_mint_unauthorized_revoke': [step(revoke, a, 'outsider')],
        'wrong_state_mint_add': [step(add, a)],
        'wrong_state_mint_revoke': [step(revoke, a)],
        'wrong_state_mint_close': [step('close_fund', signer='global')],
        'add': [step(add, a)],
        'duplicate': [step(add, a), step(add, a)],
        'capacity': [step(add, a), step(add, b), step(add, c), step(add, d)],
        'missing': [step(revoke, a)],
        'revoke': [step(add, a), step(revoke, a)],
        'hole_reuse': [step(add, a), step(add, b), step(revoke, a), step(add, c)],
        'outsider': [step(add, a, 'outsider')],
        'nonsigner': [step(add, a, flag=False)],
        'readonly': [step(add, a, writable=False)],
        'creator_close': [step('close_fund')],
        'global_close': [step('close_fund', signer='global')],
        'close_twice': [step('close_fund', signer='global'), step('close_fund', signer='global')],
        'add_after_close': [step('close_fund', signer='global'), step(add, a)],
    }
    results = []
    for name, steps in scenarios.items():
        original = run(ROOT/'evidence/mainnet.so', steps, wrong_state_mint=name.startswith('wrong_state_mint_'))
        candidate = run(ROOT/'target/deploy/dao_v1_recovered.so', steps, wrong_state_mint=name.startswith('wrong_state_mint_'))
        same = [(a['error'], a['state']) for a in original] == [(b['error'], b['state']) for b in candidate]
        results.append({'scenario': name, 'matches': same, 'original': original, 'candidate': candidate})
        print(name, 'PASS' if same else 'FAIL')
        if not same:
            print('original errors', [r['error'] for r in original])
            print('candidate errors', [r['error'] for r in candidate])
            for index, (a, b) in enumerate(zip(original, candidate)):
                diffs = [(i, x, y) for i, (x, y) in enumerate(zip(bytes.fromhex(a['state']), bytes.fromhex(b['state']))) if x != y]
                print('byte differences', index, diffs[:30])
    (ROOT/'evidence/differential-results.json').write_text(json.dumps(results, indent=2))
    assert all(r['matches'] for r in results), 'Differential mismatches: see evidence/differential-results.json'

if __name__ == '__main__':
    main()
