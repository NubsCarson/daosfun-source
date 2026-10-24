# Security audit — recovered DAO v1 program

Date: 2026-10-24. Target: `4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM`.
The captured deployment was upgradeable, with ProgramData
`DorEUwsw12hyhPGW95LrFMZTsAVi9pnjERcjQap3p7G2` at slot 370107442.
This audit concerns that captured executable, not a live view of mainnet.

The original `evidence/mainnet.so` and rebuilt `binaries/dao_v1.deployed.so`
are both 1,120,784 bytes and share SHA-256:

```text
5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d
```

The build reproduces the entire ELF and adds 79,056 generated zero-padding bytes
to match the account allocation. See [comparison evidence](../repro/final-proof.json)
and [build instructions](../docs/BUILD.md). Source references use the faithful
reconstruction under `programs/dao-v1/src`. Binary identity does not uniquely
recover the historical comments, identifiers, lockfile, or compiler settings.
**This source deliberately retains the vulnerabilities; no fix has been deployed.**

## Summary

Six findings were reproduced against the original: **one critical, four medium,
and one low**. BM-1 allows migration-fee diversion and victim lifecycle corruption
without a victim-admin signature. The medium findings require privileged actions,
off-chain approval, or particular configurations. TR-5 is a low-severity
snapshot-timing griefing defect affecting later deposits; it does not demonstrate
theft of funds already included in a snapshot.

| ID | Finding | Severity | Status | Affected instructions |
| --- | --- | --- | --- | --- |
| BM-1 | Missing DAO-to-DBC-pool binding permits migration-fee diversion and state corruption | CRITICAL | CONFIRMED_ON_ORIGINAL | `finalize_meteora_bonding` |
| TR-1 | Expiration is not enforced; holders cannot force redemption at expiry | MEDIUM | CONFIRMED_ON_ORIGINAL | `execute_invoke`, `init_redemption`, `close_fund` |
| TR-2 | Outer signer privilege, including the cosigner, is forwarded into arbitrary CPI | MEDIUM | CONFIRMED_ON_ORIGINAL | `execute_invoke` |
| TR-3 | External token authorities survive closure and can deplete snapshotted assets | MEDIUM | CONFIRMED_ON_ORIGINAL | `close_fund`, `execute_invoke`, `redeem_tokens` |
| TR-4 | Legacy-only redemption initialization is incompatible with Token-2022 funding mints | MEDIUM | CONFIRMED_ON_ORIGINAL | `init_redemption`, `close_fund` |
| TR-5 | A zero-credit caller can create a snapshot that excludes later deposits | LOW | CONFIRMED_ON_ORIGINAL; exact rebuild agrees | `burn_dao_tokens`, `redeem_sol`, `redeem_tokens` |

The unbound-pool hypothesis BM-2 was not established as an exploit in the fee-claim
and position-transfer paths. The SOL rent-remainder failure hypothesis was not
reproduced in the tested VM. A concern with nested CPI in an earlier patch is
source-level only. None is counted as another confirmed finding.

Install `requirements.txt` in a Python virtual environment, then run:

```sh
python scripts/security_tests.py
```

All six local scripts passed; [the recorded summary](results/second-pass-rerun/summary.json)
links the test names to their outcomes. These are reproductions of vulnerable
behavior, not a security certification. No mainnet transactions or real user
private keys are required. The review is not exhaustive.

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

## TR-5 — Zero-credit caller can freeze a snapshot and strand later deposits (LOW, CONFIRMED_ON_ORIGINAL)

### Root cause

[`burn_dao_tokens`](../programs/dao-v1/src/instructions/burn_dao_tokens.rs) permits
an amount of zero after redemption has started. Anchor's `init_if_needed`
creates the caller's `UserDaoBurned` account, but its escrow credit remains zero.

[`redeem_tokens`](../programs/dao-v1/src/instructions/redeem_tokens.rs) and
[`redeem_sol`](../programs/dao-v1/src/instructions/redeem_sol.rs) also accept zero.
The credit check permits `0 + 0 <= 0`, and each handler sets its asset's
`total_amount` snapshot if it was previously absent. Snapshot creation does not
require a positive credit or payout. The snapshot is never increased to account
for later deposits. Subsequent valid claims consume credit using the old balance,
including when the computed token payout is zero.

Token snapshots are specific to the treasury source token account. The SOL
snapshot is specific to the DAO's wallet. This is distinct from TR-3, which
concerns a treasury balance becoming smaller than its snapshot because an existing
authority drains it. Here the balance becomes larger than the snapshot.

### Preconditions and sequence

- Redemption has already been opened for the DAO.
- The asset has not yet had its first redemption snapshot created.
- Further funds later arrive at the same treasury wallet or source token account.
- The caller can pay transaction and metadata-account rent costs and provide the
  required initialized token accounts. The caller needs no DAO token balance,
  admin privilege, or platform cosignature for this sequence.

The test caller first invokes `burn_dao_tokens(0)` and then
`redeem_tokens(0)` / `redeem_sol(0)`. The asset token account is empty and the
wallet initially contains 1,000,000 lamports. Those balances become the snapshots.
A donor subsequently transfers 1,000,000 asset-token units and 1,000,000,000
lamports into the treasury. The honest holder escrows all 1,000 DAO token units
and claims its full recorded credit. Its token claim succeeds with a zero payout;
its SOL claim only pays the original 1,000,000-lamport snapshot.

### Evidence and control

PoC: [poc_second_redemption.py](pocs/poc_second_redemption.py).
Recorded outputs: [second-redemption.json](results/second-redemption.json).
Run: `python audit/pocs/poc_second_redemption.py`.

The script uses signed sequential local transactions against the original and
rebuilt binaries; its fixture setup is described in Methodology below.

### Recorded result

| Measurement | Early zero-amount snapshot | Control: no early snapshot |
| --- | ---: | ---: |
| Early caller's escrow credit | 0 | 0 |
| Token snapshot | 0 | 1,000,000 |
| Honest holder's asset tokens received | 0 | 1,000,000 |
| Holder's token-claim credit consumed | 1,000 | 1,000 |
| Treasury asset-token units left | 1,000,000 | 0 |
| Treasury lamports left | 1,000,000,000 | 0 |
| Another token claim for 1 credit | Error 6006 | Error 6006 |

The same script checks each scenario against both binaries and asserts equality.
The control still creates the caller's zero-credit metadata account but omits its
early redemption calls. It therefore isolates premature snapshot creation rather
than the metadata account itself. All later deposits and the honest holder's
redemption sequence are otherwise the same.

### Impact and severity

This is a **LOW-severity griefing / settlement-accounting defect** under the stated
preconditions. Later deposits can remain outside every holder's entitlement once
credits have been consumed; the reviewed program has no snapshot-refresh or
post-close general treasury-sweep path that accounts for them. The caller does not
receive the stranded tokens or lamports, and this test does not show theft of
assets that were already present when the snapshot was established.

The effect depends on deposits after redemption opens, which may be accidental
donations or an asynchronous settlement. No production settlement flow or value
at risk was established here. A real integration that necessarily settles material
assets after redemption opens would require a separate impact assessment.

### Remediation direction

Do not create or mutate redemption snapshots for a zero-credit/zero-amount caller.
Rejecting zero-value requests narrows this specific griefing path, but a positive
holder can still claim before a later deposit, so that guard alone does not solve
settlement accounting. Define when all redeemable assets are final, or use an
accounting model that distributes later arrivals without consuming holders'
additional entitlement. Do not silently burn claim credit for a zero payout unless
that behavior is explicit and accepted by the holder.

No remediation is applied to the faithful source in this repository.

---

## Negative results and unconfirmed concerns

### BM-2 — unbound `pool` in `claim_dbc_trading_fees` / `transfer_position_nft_to_fee_share` (REFUTED — hardening only)

The source pattern (unchecked `pool`) is real, but no exploit was demonstrated in
the tested paths. It is not counted as a confirmed vulnerability:
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

### SOL rent-remainder hypothesis — not reproduced

A partial SOL redemption leaving a wallet below its rent-exempt minimum was
considered as a possible dust lock. The [recorded test](results/second-redemption.json)
does not support that hypothesis for this VM configuration:

- Wallet before claim: 900,000 lamports.
- Reported minimum rent-exempt balance for zero data: 890,880 lamports.
- Claim of 100 out of 1,000 credits pays 90,000 lamports and **succeeds**.
- Wallet after that claim: 810,000 lamports, below the reported minimum.
- Claim of the remaining 900 credits also **succeeds**, leaving zero lamports.

Both the original and rebuilt binaries produce these results. This hypothesis is
not counted as a confirmed vulnerability. It is a negative result in the tested
LiteSVM environment, not proof about every validator feature set or production
runtime. Any renewed mainnet-rent claim must identify a matching runtime
configuration and reproduce the failure before assigning a severity.

### Earlier patch: nested CPI filter gap (source-level concern)

An earlier remediation experiment only filtered token approval/authority opcodes
when the immediate CPI target was SPL Token or Token-2022, while still forwarding
the wallet PDA signer to arbitrary programs. An intermediary program could invoke
the token program without passing through that first-hop filter. This was identified
by source inspection, not runtime-confirmed against the historical patched binary.
It retains the admin/delegate and cosigner preconditions and is not counted as a
new original-program finding. See [the prior patch review](PRIOR_PATCH_REVIEW.md)
for the attempted changes, historical test results and remaining design questions.

## Coverage and residual observations

The following are bounded observations, not universal absence-of-bug claims.
Several concerns remain unconfirmed or depend on external programs and product
policy. No additional HIGH finding was confirmed in the creation/admin scope.
The [scope matrix](../docs/SECURITY_SCOPE.md) records all 18 entrypoints reviewed.

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
- `cosign_update_signer` accepting a non-PDA `CosignState` is gated by CLOSE_AUTHORITY, and `execute_invoke` pins `cosign_state` to seeds `[cosigner, 0]` with canonical bump; only one 41-byte CosignState was present in the earlier captured sample. No bypass.
- `init_bonding_on_meteora`: state PDA is `init` (not re-initializable while live), `fee_authority` is bound via seeds + creator/funding_mint/dao_mint constraints, and `dbc_config` is pinned by `address = DBC_CONFIG`; no substitution in the init path (BM-1 is in finalize, not init).

**Redemption / settlement**
- Redemption solvency: `payout = snapshot*amount/current_supply`; "burned" tokens are transferred into the state-controlled escrow ATA. In the ordinary captured mint configuration without external mint-level authority effects, escrowed credits remain represented in mint supply; rounding floors in the protocol's favor; splitting claims does not increase payout.
- Double claims: `user_dao_burned` keyed by signer; SOL claims tracked in `user_sol_redeem`, token claims per `(wallet token account, signer)`; creating another wallet-owned token account does not grant another user's escrow credits. Mint-level authority and transfer-fee effects require separate analysis when a treasury holds third-party assets; the review did not establish safety for every extension.
- `redeem_sol`/`redeem_tokens` lack an explicit `redemption_started` check but require a `UserDaoBurned` PDA created only by `burn_dao_tokens` (which requires `redemption_started`); `init_if_needed` in a failing burn reverts.
- Arithmetic overflow in `dao_burn_redeemed + amount`: workspace profile sets `overflow-checks = true` and the redeem handlers normalized-match the original; no wraparound over-redemption.
- Snapshot timing: the first claim fixes a per-asset balance, including when the claim amount is zero. Later deposits can be stranded. This requires separate treatment from TR-3, which concerns balances falling after the snapshot; see TR-5 above. Donations after the snapshot are not included in holder entitlements.
- `init_redemption` carry: `carry_basis` capped at 4000 (DBC path 0), u128 math safe, runs once (`redemption_started`), pays only `state.admin`'s ATA; any signer may trigger.
- `transfer_position_nft_to_fee_share` destination is the state-derived `fee_authority` (not attacker-chosen); any-signer trigger only moves the NFT to the intended recipient.
- SOL rent remainder: the failure hypothesis was not reproduced by the local test. A partial claim leaving 810,000 lamports, below the reported 890,880-lamport rent minimum, succeeded and the remaining claim drained the wallet. This is not counted as a confirmed vulnerability; see the runtime limitation in the negative result above.
- `claim_dbc_trading_fees` after/before delta cannot underflow (claim only adds to meteora_authority ATAs) and is gated by the fee_share PDA signer (CPI-only).

---

## Methodology & limitations

- **Signatures and fixtures.** Some public-account fixture tests disable cryptographic signature verification because no real private keys are used. They still supply signer flags and execute the program authorization checks. The signed TR-5/rent test described below does not disable signature verification. Synthetic initial state is not evidence of current mainnet balances or exposure.
- **Subject.** Findings labeled CONFIRMED_ON_ORIGINAL were reproduced by running the captured original executable `evidence/mainnet.so` (sha256 `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`) in a local LiteSVM harness, with the real external programs (DBC, Token-2022, SPL Token) loaded from `evidence/`. No on-chain transaction was sent and no real wallet was used.
- **Source and binary identity.** `programs/dao-v1/src` is a reconstructed source tree. The pinned build plus explicit recovered linker layout reproduces the 951,456-byte `.text` section and the entire 1,041,728-byte ELF exactly. Generated zero padding reproduces the full captured file. This does not establish that inferred source identifiers or the historical compiler configuration are original.
- **Confidence of each finding comes from its PoC on the original**, not from the reconstruction. Where behavior depends on off-chain actors (the cosigning service in TR-2/TR-3) or external programs, the binary cannot establish that dependency, and severities above reflect that (e.g. TR-2/TR-3 need the admin + cosigner; BM-1 needs no privilege).
- **Not a formal proof.** LiteSVM local tests exercise specific inputs; they do not prove the absence of vulnerabilities, cover every Token-2022 extension or malformed-account combination, or certify production integration. Byte identity is established separately by the full binary comparison. The captured DAMM dependency used in the compatibility tests rejects `init_curve`/`migrate` fee parameters (InvalidCompoundingFeeBps 6067); BM-1's finalize path was exercised with the real captured DBC program.
- **PoC verification.** All six security scripts passed the packaged-repository rerun on 2026-10-24; see [the summary](results/second-pass-rerun/summary.json) and its individual logs. The original five finding logs are also retained under `results/first-pass-rerun/`. The outputs quoted above match the recorded local results.

### Signed snapshot and rent test setup

The TR-5 and rent-remainder test fixture uses deterministic test
keypairs, a synthetic DAO already closed and open for redemption, a basic
Token-2022 DAO mint, and a legacy-token treasury asset. Signature verification is
not disabled. The user's redemption-credit account is created by an actual
`burn_dao_tokens` instruction; it is not fabricated in account storage. Deposits
and redemptions then execute as signed transactions against the same VM state.
Transaction-history deduplication is disabled for the test harness.

This fixture does not exercise initial DAO creation, fundraising, or a real
external settlement route. It isolates what happens when assets arrive after
redemption is already open. Recorded original and rebuilt results are identical.
The packaged-repository rerun passed all six security scripts; see its [summary](results/second-pass-rerun/summary.json)
and [snapshot/rent test log](results/second-pass-rerun/poc_second_redemption.log).
These artifacts do not imply any mainnet execution or observed loss.

These tests do not cover every Token-2022 extension, validate the cosigning service,
or retest the historical remediation binary. No live funds, deployment, RPC
transaction or exploit broadcast was used.
