# Second security pass

Date: 2026-10-24. Subject: the captured original DAO program and the byte-identical
rebuilt artifact. This pass adds one confirmed **LOW** finding, TR-5, and does not
confirm the previously suggested SOL rent-remainder denial of service.

The six confirmed findings across both passes are one critical, four medium, and
one low. The [first-pass report](FIRST_PASS.md) documents BM-1 and TR-1 through
TR-4. TR-5 promotes a lower-severity snapshot observation already noted in that
report into a reproduced finding; it is not presented as a newly discovered root
cause. The [scope review](../docs/SECURITY_SCOPE.md) also covers all 18 entrypoints.

| Item | Status | Severity | Evidence |
| --- | --- | --- | --- |
| TR-5: zero-credit caller fixes a redemption snapshot before later deposits | CONFIRMED_ON_ORIGINAL and reproduced on exact rebuild | LOW | [Local signed-transaction test](pocs/poc_second_redemption.py), [results](results/second-redemption.json) |
| SOL rent remainder prevents a partial redemption | NOT REPRODUCED in this LiteSVM configuration | Not assigned | Same test's `rent_remainder` result |
| Prior patch's first-hop token-opcode filter does not cover nested CPI | Source-level remediation concern; not runtime-confirmed in this pass | Not counted as another original-program finding | [Prior patch review](PRIOR_PATCH_REVIEW.md) |

## Test method

The existing test script runs separately against `evidence/mainnet.so` and
`binaries/dao_v1.deployed.so`. Both recorded hashes are:

```text
5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d
```

All operations in these tests are local. The fixture uses deterministic test
keypairs, a synthetic DAO already closed and open for redemption, a basic
Token-2022 DAO mint, and a legacy-token treasury asset. Signature verification is
not disabled. The user's redemption-credit account is created by an actual
`burn_dao_tokens` instruction; it is not fabricated in account storage. Deposits
and redemptions then execute as signed transactions against the same VM state.
Transaction-history deduplication is disabled for the test harness.

The fixture does not exercise initial DAO creation, fundraising, or a real
external settlement route. It isolates what happens when assets arrive after
redemption is already open. Recorded original and rebuilt results are identical. The packaged repository
rerun passed all six security scripts; see its [summary](results/second-pass-rerun/summary.json)
and [second-pass log](results/second-pass-rerun/poc_second_redemption.log).
This document reports those existing local artifacts; it does not imply any
mainnet execution or observed loss.

Reproduce from the repository root after installing `requirements.txt`:

```sh
python audit/pocs/poc_second_redemption.py
```

## TR-5 — Zero-credit caller can freeze a snapshot and strand later deposits

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

### Recorded result and control

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

## SOL rent-remainder hypothesis — not reproduced

The first review mentioned that a partial SOL redemption leaving a wallet below
its rent-exempt minimum could fail and lock dust. The stored second-pass test does
not support that statement for this VM configuration:

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

## Remaining limits

These tests do not establish exhaustive security, evaluate every Token-2022
extension, validate the cosigning service, or retest the historical remediation
binary. The nested-CPI patch concern remains separately labeled as source-level
analysis. No live funds, RPC transactions, deployment or exploit broadcast were
used in this pass.
