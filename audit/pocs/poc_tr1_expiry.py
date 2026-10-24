"""TR-1 PoC: execute_invoke ignores expiration_timestamp.

Runs against the ORIGINAL evidence/mainnet.so only.
Demonstrates:
  (a) execute_invoke succeeds (moves wallet lamports via a System transfer) even
      when state.expiration_timestamp is far in the PAST and admin_closed_fund=False.
  (b) init_redemption from an ordinary signer reverts while admin_closed_fund=False
      (only CLOSE_AUTHORITY can flip it via close_fund), so holders cannot start
      redemption at/after expiry.
Both are the two halves of the "no lifecycle at expiry" claim.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from differential_execute import execute, ROOT
from differential_init_redemption import activate

ORIG = ROOT / 'evidence' / 'mainnet.so'

def main():
    print("=== TR-1 against ORIGINAL", ORIG, "===")

    # (a) execute_invoke with expiration far in the past, fund NOT closed.
    far_past = execute(ORIG, {'expiry': 1, 'amount': 500000})          # expiry = unix ts 1 (1970)
    neg = execute(ORIG, {'expiry': -1, 'amount': 500000})               # expiry = -1
    print("expiry=1 (1970)  err:", far_past['error'], "wallet_lamports_after:", far_past['wallet'])
    print("expiry=-1        err:", neg['error'], "wallet_lamports_after:", neg['wallet'])
    assert far_past['error'] is None, "expected execute_invoke to SUCCEED post-expiry"
    assert neg['error'] is None, "expected execute_invoke to SUCCEED with expiry=-1"
    # wallet started at 10**9; a successful System transfer of 500000 lamports drops it.
    assert far_past['wallet'] < 10**9, "wallet lamports should have decreased (funds moved)"
    print("=> execute_invoke moved treasury lamports AFTER expiration. No Clock/expiry check.")

    # Control: with the fund closed, execute_invoke is blocked (Execute_FundClosed), proving
    # the ONLY gate is admin_closed_fund, not time.
    closed = execute(ORIG, {'expiry': 9999999999, 'closed': True, 'amount': 500000})
    print("future expiry + closed err:", closed['error'])
    assert closed['error'] is not None, "closed fund should block execute_invoke"

    # (b) init_redemption by an ordinary signer when fund NOT closed -> reverts.
    not_closed = activate(ORIG, {'closed': 0})
    closed_ok = activate(ORIG, {'closed': 1})
    print("init_redemption closed=0 err:", not_closed['error'])
    print("init_redemption closed=1 err:", closed_ok['error'])
    assert not_closed['error'] is not None, "init_redemption should revert while not closed"
    assert closed_ok['error'] is None, "init_redemption should succeed once closed"
    print("=> Holders cannot open redemption at expiry; it requires admin_closed_fund,")
    print("   which only CLOSE_AUTHORITY sets. Expiry alone opens nothing.")
    print("TR-1 CONFIRMED on original.")

if __name__ == '__main__':
    main()
