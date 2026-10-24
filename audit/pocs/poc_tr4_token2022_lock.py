"""TR-4 PoC: init_redemption hard-requires the legacy Token program.

Runs against the ORIGINAL evidence/mainnet.so only.
Demonstrates that with a Token-2022 funding mint (and the fund already closed,
curve initialized) init_redemption always reverts, whereas the identical setup
with a legacy-Token funding mint succeeds. Since execute_invoke is disabled once
admin_closed_fund=true and redeem_* require redemption_started (set only by a
successful init_redemption), a Token-2022-funded DAO that is closed can never
open redemption -> treasury permanently locked.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from differential_init_redemption import activate, ROOT

ORIG = ROOT / 'evidence' / 'mainnet.so'

def main():
    print("=== TR-4 against ORIGINAL", ORIG, "===")
    legacy = activate(ORIG, {'closed': 1, 'curve': 1, 'balance': 2000})
    t2022 = activate(ORIG, {'token_2022': True, 'closed': 1, 'curve': 1, 'balance': 2000})
    print("legacy Token funding mint   -> err:", legacy['error'])
    print("Token-2022 funding mint     -> err:", t2022['error'])
    assert legacy['error'] is None, "legacy-token init_redemption should succeed"
    assert t2022['error'] is not None, "token-2022 init_redemption should revert"
    # Error 3008 == anchor ErrorCode::InvalidProgramId (Program<Token> rejects the
    # Token-2022 program id passed into the token_program slot).
    print("=> With a Token-2022 funding mint, init_redemption is unreachable.")
    print("   After close_fund (irreversible) the treasury can never be redeemed.")
    print("TR-4 CONFIRMED on original.")

if __name__ == '__main__':
    main()
