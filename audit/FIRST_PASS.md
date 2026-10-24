# Security Review — DAO v1 program `4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM`

Date: 2026-10-24
Scope: on-chain behavior of the deployed mainnet program (upgradeable; ProgramData `DorEUwsw12hyhPGW95LrFMZTsAVi9pnjERcjQap3p7G2`, captured deployment slot 370107442).
Subject under test: the captured original executable `evidence/mainnet.so`
(1,120,784 bytes, sha256 `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`).

All findings labeled **CONFIRMED_ON_ORIGINAL** were reproduced by executing the
captured original executable in local LiteSVM. No on-chain transactions or real
wallet signatures were used. Some public-account fixtures disable signature
cryptography; the program's signer flags and authorization checks still execute.

Source references now point to the faithful reconstruction under `programs/dao-v1/src`.
A clean source build with the pinned toolchain and recovered linker ordering matches
the original ELF byte for byte. The full captured account allocation also matches
after adding its 79,056 zero-padding bytes. See [the comparison evidence](../repro/final-proof.json)
and [build instructions](../docs/BUILD.md). This proves binary reconstruction, not
unique recovery of the historical source names, comments, lockfile, or build flags.
The faithful source intentionally retains these vulnerabilities.

This document preserves the five first-pass findings. The [second pass](SECOND_PASS.md)
and [scope notes](../docs/SECURITY_SCOPE.md) refine remaining risks; this is not an
assertion that every vulnerability has been found.
---

## Executive summary

One **CRITICAL** issue allows an unprivileged attacker to permanently redirect a
DAO's one-shot Meteora migration fee into a treasury the attacker controls, and to
brick an arbitrary victim DAO's lifecycle. The remaining four confirmed issues are
**MEDIUM**: each is a real on-chain defect but requires a privileged precondition
(the hard-coded CLOSE_AUTHORITY, the admin plus the platform cosigner) or an unusual
configuration, so none is an unprivileged single-actor theft on its own.

| ID | Title | Severity | Status | Affected instructions |
| --- | --- | --- | --- | --- |
| BM-1 | `finalize_meteora_bonding` does not bind the DBC `pool` to the DAO state: migration fee theft + victim-state corruption | CRITICAL | CONFIRMED_ON_ORIGINAL | `finalize_meteora_bonding` |
| TR-1 | `execute_invoke` ignores `expiration_timestamp`; holders cannot force redemption at expiry | MEDIUM | CONFIRMED_ON_ORIGINAL | `execute_invoke`, `init_redemption`, `close_fund` |
| TR-2 | `execute_invoke` forwards the cosigner's (and every outer signer's) signature into the arbitrary CPI | MEDIUM | CONFIRMED_ON_ORIGINAL | `execute_invoke` |
| TR-3 | `close_fund` does not neutralize pre-installed delegations/close authorities; `redeem_tokens` does not reject them or cap payouts at live balance | MEDIUM | CONFIRMED_ON_ORIGINAL | `close_fund`, `execute_invoke`, `redeem_tokens`, `init_redemption` |
| TR-4 | `init_redemption` hard-requires legacy Token program; a Token-2022 funding mint + `close_fund` permanently locks the treasury | MEDIUM | CONFIRMED_ON_ORIGINAL | `init_redemption` (reachable via `initialize`/`start_raise`/`init_curve`), `close_fund` |
| BM-2 | Same unbound-`pool` pattern in `claim_dbc_trading_fees` / `transfer_position_nft_to_fee_share` | N/A | REFUTED (hardening only) | `claim_dbc_trading_fees`, `transfer_position_nft_to_fee_share` |

Install `requirements.txt` in a Python virtual environment, then run `python scripts/security_tests.py`.
The individual PoCs below can also be run directly. The five first-pass PoCs were
re-run on 2026-10-24; the current run logs are in `audit/results/first-pass-rerun/`.

---

## BM-1 — `finalize_meteora_bonding` accepts any DBC pool (CRITICAL, CONFIRMED_ON_ORIGINAL)

### Description
`FinalizeMeteoraBonding` validates the DAO `state` (seeds `[b"state", token_mint]`,
`state.dao_mint == token_mint`, `state.funding_mint == funding_mint`,
`curve_initialized == false`) and the DBC quote vault/mint, but the `pool` account
itself is a caller-supplied `#[account(mut)] UncheckedAccount` with **no constraint
tying it to `token_mint` or to this DAO's `state`**. The `withdraw_migration_fee` CPI
touches only the quote side (`config = DBC_CONFIG`, `virtual_pool = pool`,
`quote_mint = funding_mint`, `quote_vault = pool_funding_vault` derived from the
*shared* `funding_mint` + the attacker-chosen `pool`, destination
`token_quote_account = wallet_funding_ata`, the supplied state's treasury ATA). The
CPI sender is the **global** `meteora_authority` PDA (seeds `[b"meteora_authority"]`),
the same fee-sender for every DAO, and the program signs with it. Because the funding
mint (e.g. WSOL) is shared across DAOs and the sender PDA is global, DBC accepts a
foreign pool and pays its migration fee into the attacker's treasury. The handler then
unconditionally writes `state.funding_goal = config.migration_quote_threshold` and
`state.curve_initialized = true` onto whichever `state` was supplied.

### Root cause (source refs)
- `programs/dao-v1/src/instructions/bonding/finalize_meteora_bonding.rs` (`FinalizeMeteoraBonding`) — `struct FinalizeMeteoraBonding`: `pool: UncheckedAccount` with no identity tie to `token_mint`/`state`, and a bare `signer: Signer<'info>` with no admin or state-ownership constraint.
- `programs/dao-v1/src/instructions/bonding/finalize_meteora_bonding.rs` (`finalize`) — handler builds the `withdraw_migration_fee` CPI over the quote side only and unconditionally writes `funding_goal`/`curve_initialized` onto the supplied `state`.

The single missing check is a binding of `pool` to the DAO mint pair. `TransferPositionNftToFeeShare` already does this correctly (typed pool load + `pool.token_a_mint == token_mint && pool.token_b_mint == funding_mint`), which is the template for the fix.

### Attack (step by step)
1. Attacker calls `init_bonding_on_meteora` to create their own DAO Y, becoming `Y.admin` with an attacker-controlled treasury wallet PDA / `wallet_funding_ata`.
2. A legitimate DAO X reaches its DBC migration threshold (pool X ready for `WithdrawMigrationFee`).
3. Attacker calls `finalize_meteora_bonding` with `state = Y`, `wallet_funding_ata = Y`'s treasury, but `pool`/`pool_funding_vault`/`pool_token_vault` for DAO X (same shared `funding_mint`). No signer/admin relationship to X is needed — `signer` has no admin check.
4. DBC transfers X's one-shot migration fee into Y's treasury.
5. X's own `finalize_meteora_bonding` now reverts with Custom 6040 (fee already withdrawn); X has permanently lost its migration fee.

Variant (lifecycle DoS): supply `state = victim` (a not-yet-finalized DAO, `curve_initialized` still false) with any completed pool to flip `victim.curve_initialized = true` and overwrite `funding_goal`, permanently blocking the victim's real `init_curve`/`start_raise`/`migrate` paths (all require `curve_initialized == false`).

### Impact (who loses what)
Permanent, unrecoverable redirection of a DAO's migration fee (treasury funds) into an
attacker-controlled treasury, by an unprivileged actor with no relationship to the
victim DAO — the DBC withdrawal is one-shot, so the rightful DAO can never reclaim it.
Additionally, the attacker can corrupt `funding_goal` and permanently set
`curve_initialized = true` on an arbitrary victim `state`, locking that DAO's lifecycle.

### Evidence
PoC: `audit/poc_finalize_cross_pool.py`
Run: `python audit/poc_finalize_cross_pool.py`
(executes against `evidence/mainnet.so` with the captured DBC program in LiteSVM).
Observed (re-run 2026-10-24, original binary):
```
Y wallet before 100 Y curve_initialized (0, 1234)
attacker finalize(Y state, X pool) err = None
Y wallet after 1100 Y curve_initialized (1, 10000)
honest finalize(X state, X pool) err = {'InstructionError': [0, {'Custom': 6040}]} X curve_initialized (0, 1234) X wallet 100
```
The transaction signer (not required to be either DAO's admin) redirected 1000 funding-token units of DAO X's
migration fee into DAO Y's treasury (wallet 100 → 1100), flipped `Y.curve_initialized`
0 → 1, overwrote `Y.funding_goal` 1234 → 10000, and X's own finalize then permanently
reverts with Custom 6040.

### Fix (code-level)
In `FinalizeMeteoraBonding`, load the DBC `virtual_pool` as a typed zero-copy account
and require `pool.base_mint == token_mint.key()` and `pool.quote_mint == funding_mint.key()`
— analogous to the typed DAMM pool binding used by `TransferPositionNftToFeeShare` — or derive and verify
the DBC pool PDA from `config + token_mint + funding_mint`. Additionally gate finalize to
the DAO admin (`require!(state.admin == signer.key(), ...)`). Either binding alone closes
the cross-pool substitution; the admin gate is defense in depth.

### Operational mitigation without a program upgrade
Because exploitation requires the attacker to beat the rightful DAO to the one-shot
`WithdrawMigrationFee`, the platform can monitor DBC pools approaching threshold and
submit the honest `finalize_meteora_bonding` for each DAO as soon as it is eligible,
denying the front-run window. This is a race mitigation, not a fix; a redeploy with the
pool binding is required to actually remove the vulnerability.

---

## TR-1 — `execute_invoke` ignores `expiration_timestamp`; holders cannot force redemption at expiry (MEDIUM, CONFIRMED_ON_ORIGINAL)

### Description
The error names (`6012 Execute_FundExpired`, `6007 Redeem_FundNotExpired`) suggest
a lifecycle where treasury execution stops at expiration and redemption opens; error
names alone do not establish an external product promise.
The deployed code enforces neither. `handle_execute_invoke` checks only
`!admin_closed_fund` and that the authority is in `{admin, delegates}`; it reads no
`Clock` and never compares `state.expiration_timestamp`. `init_redemption` requires
`admin_closed_fund`, which only the hard-coded CLOSE_AUTHORITY sets via `close_fund`.
Error 6012 is dead code (no `0x177c` in the disassembly, no clock syscall in the handler).

### Root cause (source refs)
- `programs/dao-v1/src/instructions/execute_invoke.rs` (`handle_execute_invoke`) — gate is `!admin_closed_fund` + authority membership only; no `Clock::get`, no expiration comparison.
- `programs/dao-v1/src/instructions/init_redemption.rs` (`handle_init_redemption`) — requires `admin_closed_fund` else error 6007.
- `programs/dao-v1/src/lib.rs` (`close_fund`): closure is a privileged state transition, not a clock-triggered one.

### Attack
1. A creator raises with a short `dao_duration_seconds`.
2. After `expiration_timestamp` passes, the creator or a delegate keeps calling `execute_invoke` (with the platform cosigner's co-signature) to move treasury assets.
3. Holders calling `init_redemption` revert with 6007 because only CLOSE_AUTHORITY can set `admin_closed_fund`.

### Impact
A holder-enforceable time-based lifecycle does not exist on-chain: the treasury stays admin +
cosigner custodial for the fund's entire life, and holders have no on-chain path to force
redemption at the fund's term. This is a missing lifecycle/exit guarantee, **not** a new
drain capability — every `execute_invoke` still requires both the admin/delegate and the
platform cosigner, before and after expiry.

### Evidence
PoC: `audit/pocs/poc_tr1_expiry.py`
Run: `python audit/pocs/poc_tr1_expiry.py`. Observed (re-run 2026-10-24):
```
expiry=1 (1970)  err: None wallet_lamports_after: 999500000
expiry=-1        err: None wallet_lamports_after: 999500000
future expiry + closed err: {'InstructionError': [0, {'Custom': 6013}]}
init_redemption closed=0 err: {'InstructionError': [0, {'Custom': 6007}]}
init_redemption closed=1 err: None
```
`admin_closed_fund`, not time, is the sole gate (closed → Custom 6013 Execute_FundClosed; redemption opens only when closed).

### Fix
In `execute_invoke` add `require!(Clock::get()?.unix_timestamp < state.expiration_timestamp, Execute_FundExpired)`.
In `init_redemption` accept `admin_closed_fund || now >= expiration_timestamp` so anyone
may open redemption after expiry and `execute_invoke` stops at expiry.

### Operational mitigation without a program upgrade
The CLOSE_AUTHORITY can call `close_fund` at (or near) a fund's intended term to stop
`execute_invoke` and open redemption. This substitutes an off-chain operator action for
the missing on-chain gate; it does not restore a holder-driven exit.

---

## TR-2 — `execute_invoke` forwards the cosigner's outer signature into the arbitrary CPI (MEDIUM, CONFIRMED_ON_ORIGINAL)

### Description
`handle_execute_invoke` builds each CPI `AccountMeta` with
`is_signer = (key == wallet) || account.is_signer` and clones remaining-account
`AccountInfo`s preserving `is_signer`. The cosigner is a required outer signer of
`execute_invoke` (`ExecuteInvoke.cosigner: Signer`), so its signer privilege is always
forwarded into the arbitrary admin-chosen CPI (`instruction_program` + `instruction_data`
are fully attacker-controlled). Any invoked program can treat the cosigner as an
authorizing signer (SPL-Token Transfer/Approve/SetAuthority, Jupiter swaps, etc.). One
cosigner key is shared by every DAO (`cosign_state` id 0).

### Root cause (source refs)
- `programs/dao-v1/src/instructions/execute_invoke.rs` (CPI account metas and infos) — `is_signer` propagation for metas and `is_signer = true`-preserving clone for infos.
- `programs/dao-v1/src/instructions/execute_invoke.rs` (`ExecuteInvoke`) — `ExecuteInvoke.cosigner: Signer` forced outer signer.
- `evidence/full-account-samples.json` and `evidence/related-accounts.json` (shared cosigner `AeqZQ...`).

### Attack
1. A malicious DAO admin builds `execute_invoke` targeting another program (for example, Token) and lists the cosigner pubkey in `remaining_accounts` as the source authority.
2. If its off-chain policy approves this payload, the cosigning service co-signs; without that signature the call cannot execute.
3. Inside the CPI the cosigner counts as a signer, so the admin moves the cosigner's own tokens, or exercises any authority the cosigner key holds, to an attacker account.

### Impact
Theft of any assets or authorities held by the shared platform cosigner key, and abuse
of cosigner-gated permissions in other programs, by any DAO admin whose transaction the
cosigning service approves. **Impact is zero if the cosigner key holds no assets and
controls no other authority**, and is contingent on the off-chain cosigning policy
approving an attacker-shaped payload. Escalates to HIGH if the cosigner key is found to
control funds or delegations.

### Evidence
PoC: `audit/pocs/poc_tr2_cosigner_signer.py`
Run: `python audit/pocs/poc_tr2_cosigner_signer.py`. Observed (re-run 2026-10-24):
```
attack  (authority = cosigner, a forced outer signer): None victim_balance: 0 attacker_balance: 1000
control (authority = fresh key that signed nothing)  : {'InstructionError': [0, 'MissingRequiredSignature']} victim_balance: 1000
```
The cosigner's own tokens moved via `execute_invoke` → Token TransferChecked with the
cosigner as authority; the control with a non-signer authority fails with
`MissingRequiredSignature`, isolating signature forwarding as the cause.

### Fix
Do not propagate outer signer flags: set `is_signer = (key == wallet)` only, and
explicitly reject remaining accounts equal to `cosigner`, `authority`, `state`, or
`cosign_state`.

### Operational mitigation without a program upgrade
Keep the shared cosigner key free of assets and of any other on-chain authority, and have
the cosigning service reject transactions that list the cosigner among inner CPI accounts.
This removes the realizable loss without a redeploy, but the forwarding mechanism remains.

---

## TR-3 — `close_fund` does not neutralize pre-installed delegations; `redeem_tokens` does not reject them or cap payouts (MEDIUM, CONFIRMED_ON_ORIGINAL)

### Description
`close_fund` only sets `admin_closed_fund = true` (which makes `execute_invoke` refuse to
run); it does not revoke SPL-Token delegates, close authorities, or owner changes installed
earlier on wallet-owned accounts. `redeem_tokens` places no
`delegate.is_none()`/`close_authority.is_none()` constraint on the treasury token account,
takes the redemption snapshot lazily on the first claim (`total_amount = current balance`),
and never re-checks payouts against the live balance. A delegate pre-armed through
`execute_invoke` (admin + cosigner) therefore survives close and can drain the treasury
directly via SPL Token, with no dao_v1 instruction involved; once the balance falls below
the lazy snapshot, later redeemers compute `payout = snapshot*amount/supply` and revert on
insufficient funds while earlier redeemers were paid in full.

### Root cause (source refs)
- `programs/dao-v1/src/instructions/redeem_tokens.rs` — lazy snapshot (lines 23-25), payout from snapshot (line 30), no delegate/close-authority constraint on the `RedeemTokens` treasury account.
- `programs/dao-v1/src/instructions/init_redemption.rs` — opens redemption after paying carry; it does not revoke delegates or snapshot each asset. Per-asset balances are captured later by the redeem handlers.
- `programs/dao-v1/src/lib.rs` (`close_fund`) — `close_fund` sets only `admin_closed_fund`.

### Attack
1. Malicious admin/delegate calls `execute_invoke` with an SPL Approve of the wallet funding ATA to an attacker delegate for `u64::MAX`; the cosigner co-signs the innocuous-looking approval.
2. CLOSE_AUTHORITY closes the fund to protect holders; `init_redemption` runs, then the first claim snapshots the asset balance.
3. The attacker drains the ATA with a direct delegate TransferChecked — nothing in dao_v1 can revoke it because `execute_invoke` is now disabled.
4. Late redeemers' `redeem_tokens` calls revert against the stale snapshot while early redeemers kept their payouts.

### Impact
Treasury theft that survives the platform's protective close, plus mis-accounted
redemptions where some holders are paid and later holders are stranded. The post-close
drain still requires the admin plus the platform cosigner to pre-arm the delegate (no
unprivileged path), which is why this is MEDIUM. (The migration handlers explicitly permanently lock DAMM liquidity positions;
this finding does not classify that explicit behavior as a defect.)

### Evidence
PoC: `audit/pocs/poc_tr3_delegate_snapshot.py`
Run: `python audit/pocs/poc_tr3_delegate_snapshot.py`. Observed (re-run 2026-10-24):
```
A: execute_invoke SPL Approve err: None
B: direct delegate drain err: None treasury_after: 0 attacker_after: 1000000
C1: redeem against delegated+close-authority treasury acct err: None
C2: redeem with stale snapshot (snapshot=1e6, live=1) err: {'InstructionError': [0, {'Custom': 1}]}
```
A+B: close cannot revoke a pre-armed delegate; the attacker drains the ATA. C1:
`redeem_tokens` accepts a treasury account carrying both a delegate and a close authority.
C2: a stale snapshot over a reduced live balance reverts with Token Custom 1 (insufficient
funds), stranding late redeemers.

### Fix
In `init_redemption` (or `close_fund`) reject unsafe delegate/native-close-authority states and provide a way to clear them.
Restrict authorization-changing actions across the entire CPI call tree, not only the
first instruction. Define how depleted balances and later deposits affect all holders
before changing payout calculations: a simple live-balance cap can silently favor
early claimants. See [the prior patch review](PRIOR_PATCH_REVIEW.md) for residual gaps.

### Operational mitigation without a program upgrade
Before closing a fund, the operator/cosigning service should refuse Approve/SetAuthority
payloads through `execute_invoke`, and should revoke any outstanding delegate/close
authority on treasury token accounts (via a final `execute_invoke` Revoke) before
`close_fund`, since close itself cannot revoke them.

---

## TR-4 — Token-2022 funding mint + `close_fund` permanently locks the treasury (MEDIUM, CONFIRMED_ON_ORIGINAL)

### Description
`InitRedemption` declares `token_program: Program<anchor_spl::token::Token>` and
constrains both funding ATAs with `associated_token::token_program = token_program`,
pinning the funding mint to the legacy SPL Token program. But `initialize` (funding mint is
an unconstrained `InterfaceAccount`), `start_raise`, and `init_curve` all accept
`funding_token_program: Interface<TokenInterface>`, so a Token-2022 funding mint can pass
through the entire creation/curve lifecycle and reach `curve_initialized = true`. After the
irreversible `close_fund`, `execute_invoke` is disabled, `init_redemption` can never
succeed for a Token-2022 funding mint, and `redeem_*` require `UserDaoBurned` PDAs that only
`burn_dao_tokens` (which needs `redemption_started`) creates. All treasury SOL and tokens
are then locked permanently.

### Root cause (source refs)
- `programs/dao-v1/src/instructions/init_redemption.rs` (`InitRedemption`) — `Program<Token>` + `associated_token::token_program = token_program` on both funding ATAs.
- `programs/dao-v1/src/instructions/init.rs` (`Initialize`) — `funding_mint` unconstrained.
- `programs/dao-v1/src/instructions/start_raise.rs` (`StartRaise`), `programs/dao-v1/src/curve_accounts.rs` (`InitCurve`) — `funding_token_program: Interface<TokenInterface>`.

### Attack
1. A creator initializes and raises with a Token-2022 funding mint (e.g. PYUSD); the type signatures permit it.
2. The platform later calls `close_fund`.
3. `init_redemption` reverts with 3008 on every attempt, `redemption_started` is never set, and all treasury funds become permanently unredeemable.

### Impact
Permanent lock of all treasury SOL and tokens for any DAO created with a Token-2022 funding
mint and subsequently closed. No theft and no cross-DAO impact; the loss is confined to that
DAO's own holders and triggered by the platform's close action. MEDIUM because it requires an
unusual funding-mint configuration (all observed mainnet DAOs use WSOL) self-selected by the
creator; HIGH if any live or planned Token-2022-funded DAO exists.

### Evidence
PoC: `audit/pocs/poc_tr4_token2022_lock.py`
Run: `python audit/pocs/poc_tr4_token2022_lock.py`. Observed (re-run 2026-10-24):
```
legacy Token funding mint   -> err: None
Token-2022 funding mint     -> err: {'InstructionError': [0, {'Custom': 3008}]}
```
Identical closed + curve-initialized setup: legacy-Token funding mint opens redemption;
Token-2022 funding mint reverts with Custom 3008 (InvalidProgramId).

### Fix
Use `Interface<TokenInterface>` for `init_redemption`'s `token_program` (and the funding
ATAs), **or** reject Token-2022 funding mints at `initialize`/`start_raise`/`init_curve` so
the unredeemable state is never reachable.

### Operational mitigation without a program upgrade
Do not create or allow DAOs with a Token-2022 funding mint until a redeploy fixes the
interface; if such a DAO exists, do not call `close_fund` on it (the lock only materializes
after close). The platform can enforce a WSOL-only funding mint in its UI/cosigning policy.

---

## Refuted findings

### BM-2 — unbound `pool` in `claim_dbc_trading_fees` / `transfer_position_nft_to_fee_share` (REFUTED — hardening only)
The source pattern (unchecked `pool`) is real, but no illegal state change or fund movement
is constructible on the original, so it is not a live vulnerability:
- `token_mint` is a fresh per-DAO `Signer` created in `init_bonding_on_meteora`, and the DBC/DAMM pool PDA is deterministic in `(config, token_mint, funding_mint)`, so each DAO has exactly one pool over its mint pair — a DAO cannot hold two pools over the same pair.
- `claim_dbc_trading_fees`: DBC's `ClaimTradingFee` validates `base_mint == token_mint`; and `fee_authority` carries a `signer` constraint with `seeds::program = fee_share_trader_dao::ID`, so the handler is only reachable via CPI from the fee-share program, and the claimed deltas go to fixed `fee_authority` ATAs, not an attacker-chosen sink.
- `transfer_position_nft_to_fee_share`: `pool` is a typed `AccountLoader` with `pool.token_a_mint == token_mint && pool.token_b_mint == funding_mint` and `position.pool == pool`, and the SetAuthority target is the state-derived `meteora_authority`/`fee_authority`.

Recommendation (defense in depth, not a fix for a live bug): bind `pool` to the DAO in both
handlers as BM-1's fix does — load the DBC/DAMM pool as typed state and assert
`base_mint == token_mint && quote_mint == funding_mint` in-program rather than relying solely
on the external program's checks.

Source refs: `programs/dao-v1/src/instructions/bonding/claim_dbc_trading_fees.rs`
(`ClaimDbcTradingFees`) and `programs/dao-v1/src/instructions/bonding/transfer_position_nft_to_fee_share.rs`
(`TransferPositionNftToFeeShare`).

---

## First-pass coverage and residual observations

The following are bounded first-pass observations, not universal absence-of-bug claims.
Several lower-severity concerns were recorded without a dedicated first-pass finding.
See the [second pass](SECOND_PASS.md) for additional reproduction and updated treatment.
No additional HIGH finding was confirmed in the creation/admin scope during this pass.

**Creation / curve / admin**
- `migrate_bonding_to_meteora` has no admin check on `payer`, but an outsider cannot create a hedgefun curve for someone else's DAO state: the curve PDA is `[b"curve", depositor]` and the depositor must sign; in migrate the depositor/authority is the state PDA and there is no CPI into hedgefun `Init`, so only legacy curves reach migration. No hijack via forced `curve_initialized = true`.
- `migrate_bonding_to_meteora` fund flows balance out (curve funding in; DAMM pool + 20% reserve to wallet out); hedgefun enforces `complete == true` and `migrated == false`; the stale hedgefun_curve account is owned by another program and not written back.
- DAMM pre-funding DoS on `position_nft_mint`/`pool`/`position` PDAs: cp-amm uses Anchor `init`, which tolerates pre-funded lamports; `fee_nft_account` is ATA-created after the mint exists in the same tx, so it cannot be pre-created.
- `init_curve`: signer must be `state.admin` or the hard-coded OPERATOR; fundraise_state PDA and `is_finalized` are checked. The creator buy via `additional_funding` is a constant-product swap at the initial price (skips the DAMM anti-sniping cliff fee but takes no holder value); `TooHighSnipingAmount` is defined but unused. Policy concern, below HIGH.
- `init_curve` uses `state.funding_goal` rather than the actual vault balance; any over-goal amount stays in `state_funding_vault`, which has no withdrawal path in the reviewed source. Depends on the external fundraise program (not verified); possible lock, low confidence, not known-HIGH.
- `initialize`: `dao_mint` is a new init signer keypair; front-running `fee_share_state` for a known mint key is DoS only, fixed by a new keypair. `funding_mint` is not whitelisted, so a creator could pick a Token-2022 mint with permanent delegate/freeze authority — a trust/UI risk for depositors, not a program bypass.
- `start_raise` is admin-only, requires `curve_initialized == false`, and running it twice fails in the fundraise program's init.
- `add_delegate_authority` / `revoke_delegate_authority` require `state.admin` as signer and a matching state PDA; duplicate check reverts the whole tx; delegates cannot add delegates; `execute_invoke` still requires the cosigner.
- `close_fund` is gated to the hard-coded CLOSE_AUTHORITY, one-way, and only enables redemption (which itself requires `curve_initialized`).

**State layout / cosigner**
- Legacy 697-byte State accounts (34 in the earlier captured sample) carry the same discriminator but a different layout; the sampled accounts did not deserialize under the recovered layout (borsh rejects the bool/Option tags), so they cannot be confused into fake admins/delegates.
- `cosign_update_signer` accepting a non-PDA `CosignState` is gated by CLOSE_AUTHORITY, and `execute_invoke` pins `cosign_state` to seeds `[cosigner, 0]` with canonical bump; only one 41-byte CosignState exists on mainnet. No bypass.
- `init_bonding_on_meteora`: state PDA is `init` (not re-initializable while live), `fee_authority` is bound via seeds + creator/funding_mint/dao_mint constraints, and `dbc_config` is pinned by `address = DBC_CONFIG`; no substitution in the init path (BM-1 is in finalize, not init).

**Redemption / settlement**
- Redemption solvency: `payout = snapshot*amount/current_supply`; "burned" tokens are transferred into the state-controlled escrow ATA. In the ordinary captured mint configuration without external mint-level authority effects, escrowed credits remain represented in mint supply; rounding floors in the protocol's favor; splitting claims does not increase payout.
- Double claims: `user_dao_burned` keyed by signer; SOL claims tracked in `user_sol_redeem`, token claims per `(wallet token account, signer)`; creating another wallet-owned token account does not grant another user's escrow credits. Mint-level authority and transfer-fee effects require separate analysis when a treasury holds third-party assets; the first pass did not establish safety for every extension.
- `redeem_sol`/`redeem_tokens` lack an explicit `redemption_started` check but require a `UserDaoBurned` PDA created only by `burn_dao_tokens` (which requires `redemption_started`); `init_if_needed` in a failing burn reverts.
- Arithmetic overflow in `dao_burn_redeemed + amount`: workspace profile sets `overflow-checks = true` and the redeem handlers normalized-match the original; no wraparound over-redemption.
- Snapshot timing: the first claim fixes a per-asset balance, including when the claim amount is zero. Later deposits can be stranded. This requires separate treatment from TR-3, which concerns balances falling after the snapshot; see the second pass. The earlier blanket assertion that donations benefit all holders was too broad.
- `init_redemption` carry: `carry_basis` capped at 4000 (DBC path 0), u128 math safe, runs once (`redemption_started`), pays only `state.admin`'s ATA; any signer may trigger.
- `transfer_position_nft_to_fee_share` destination is the state-derived `fee_authority` (not attacker-chosen); any-signer trigger only moves the NFT to the intended recipient.
- SOL rent remainder: the first-pass failure hypothesis was not reproduced by the second-pass test. A partial claim leaving 810,000 lamports, below the reported 890,880-lamport rent minimum, succeeded and the remaining claim drained the wallet. This is not counted as a confirmed vulnerability; see the second-pass runtime limitation.
- `claim_dbc_trading_fees` after/before delta cannot underflow (claim only adds to meteora_authority ATAs) and is gated by the fee_share PDA signer (CPI-only).

---

## Methodology & limitations

- **Subject.** Findings labeled CONFIRMED_ON_ORIGINAL were reproduced by running the captured original executable `evidence/mainnet.so` (sha256 `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`) in a local LiteSVM harness, with the real external programs (DBC, Token-2022, SPL Token) loaded from `evidence/`. No on-chain transaction was sent and no real wallet was used.
- **Source and binary identity.** `programs/dao-v1/src` is a reconstructed source tree. The pinned build plus explicit recovered linker layout reproduces the 951,456-byte `.text` section and the entire 1,041,728-byte ELF exactly. Generated zero padding reproduces the full captured file. This does not establish that inferred source identifiers or the historical compiler configuration are original.
- **Confidence of each finding comes from its PoC on the original**, not from the reconstruction. Where behavior depends on off-chain actors (the cosigning service in TR-2/TR-3) or external programs, the binary cannot establish that dependency, and severities above reflect that (e.g. TR-2/TR-3 need the admin + cosigner; BM-1 needs no privilege).
- **Not a formal proof.** LiteSVM local tests exercise specific inputs; they do not prove the absence of vulnerabilities, cover every Token-2022 extension or malformed-account combination, or certify production integration. Byte identity is established separately by the full binary comparison. The captured DAMM dependency used in the compatibility tests rejects `init_curve`/`migrate` fee parameters (InvalidCompoundingFeeBps 6067); BM-1's finalize path was exercised with the real captured DBC program.
- **PoC verification.** All five confirmed PoC files were verified to exist and were re-run on 2026-10-24; the outputs quoted above are from that run and match the recorded summaries.
