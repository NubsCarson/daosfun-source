# DAO v1: independent versioned replays and binding checks

The current `dao_v1` ProgramData ELF captured by this lab is SHA-256
`5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`,
byte-identical to this repository's original capture and rebuilt binary.
Of 18 current site-IDL selectors, **17** have a bounded successful local
path on the exact current DAO binary. `init_curve` has a successful restored
source-era DAO/CPMM replay only; sampled current-binary replays fail in the
downstream CPMM path. Thus 18/18 have a bounded success across versions and
0/18 are certified full behavior. The [per-handler binary provenance](receipts/dao-v1-binary-provenance.json)
pins the ELF hash and receipt for each claim. Exact source recovery materially improves
review, but this lab has not closed all
reachable account, authority, math, historical-version and error branches.
Original receipt filenames below are inside the
[daos.fun evidence bundle](daosfun-lab-evidence.tar.zst).

## Current DAO/DBC pool binding

The [published audit](../../audit/AUDIT.md) calls out an unbound DBC pool in
`finalize_meteora_bonding` (BM-1). An independent local fixture loaded **this
lab's** pinned current DAO and DBC ELFs, two distinct captured migrated DBC
pools and DAO States, and a genuinely signed disposable payer. Finalizing
DAO X with X's pool succeeded. On fresh local state, finalizing **DAO Y with
X's pool** also succeeded: X's pool migration-fee status moved 0→4 while Y's
`curve_initialized` moved 0→1 and `funding_goal` 0→66,000,000,000. X's later
honest finalize failed DBC 6040. This confirms an unprivileged cross-pool
lifecycle/state-binding flaw in the current binary under the tested account
layout. The saved DBC config's migration-fee field is **zero** and the
captured quote vault/treasury balances did not change, so this independent
fixture does **not** prove presently diverted treasury tokens. In an
**explicitly synthetic** config with migration-fee byte 10, the same local
route moves 6.6 billion raw funding units from X's quote vault into Y's
treasury before X's honest finalize fails. This isolates the conditional
fee-diversion mechanism. See the [signed cross-pool receipt](receipts/dao-bm1-cross-pool-current-config.json)
(`analysis/daos_fun/dao-bm1-cross-pool-current-config.json`) and
`scripts/daos_dao_bm1_cross_pool.py`.

The code mechanism is consistent with the published source: the handler
checks the supplied DAO State but takes a caller-chosen pool, then uses one
global `meteora_authority` PDA for the DBC fee-withdrawal CPI. A fee-bearing
configuration and a still-withdrawable pool are separate prerequisites for
current fund diversion. A later finalized [three-pool sample](receipts/dao-bm1-current-exposure-snapshot.json), not a
network-wide census, found three migrated DBC pools still at migration-fee
status zero paired with unfinalized DAO States; the same deployed DBC config
had fee byte zero. See `dao-bm1-current-exposure-snapshot.json`. No mainnet
transaction was sent.

## Issuance and historical versions

One sampled DAO mint initially received exactly `1e18` raw units at
`Initialize`, followed by `100e15` at a **source-era** `InitCurve`. Its later
captured supply of `1,099,887,774,968,560,241` is below that combined
issuance, so the first `+100e15` above initialization is explained; the
remaining historical MintTo/Burn sequence has not been fully attributed.
The source transaction's `InitCurve` had a different account layout from the
current IDL. `analysis/daos_fun/dao-v1-mint-issuance-source.json` preserves
the transaction/signature and deployment boundaries.

For an older DAO ELF reconstructed from archived upgrade-buffer writes,
`InitCurve` at slot 366145612 matches all nine watched post-token balances
and eleven changed lamport balances of the historical transaction when the
known later account state is inverse-restored. Thirteen selected branch
cases include signer guards and snipe amounts. The tested token quote is
`floor(150e15 × snipe / (336e9 + snipe))`; large synthetic snipe balances
are not evidence of a real funded opportunity. A separate source-era
`MigrateBondingToMeteora` replay matches nine post-token and ten changed
lamport balances, with explicit state restoration. See
`dao-v1-init-curve-source-era-binaries-replay.json`,
`dao-v1-init-curve-snipe-matrix.json`, and
`dao-v1-migrate-bonding-historical-dao-restored-replay.json`.

An even older `LegacyToRaydium` wrapper is present in a historical DAO ELF
but dispatches to fallback 101 in the current one. Its source-era local
replay matched recorded balances; recipient redirection did not yield a
retained caller gain under the tested wrapper and locked-LP path. Current
generic `ExecuteInvoke` reaches VirtualXYK migration but cannot sign the
required State/depositor PDA in the tested route. Historical wrapper
behavior must not be projected onto the current binary. See
`dao-legacy-wrapper-source-era-replay.json`,
`dao-legacy-wrapper-redirect-locked-lp.json`, and
`analysis/root_virtual_xyk/dao-execute-virtual-migrate.json`.

## Other bounded paths

Synthetic `Initialize` plus `StartRaise` calls create the expected State,
DAO mint, fee share, and Fundraise accounts under pinned binaries. Carry
basis 4000 succeeds while 4001 rejects in tested cases. Zero funding goal
passes `Initialize` but a later `StartRaise` reaches a Fundraise
divide-by-zero panic and rolls back. This is an account/configuration hazard
observed locally, not a confirmed current user loss.

Delegate/cosigner lifecycle, redemption, DBC fee claims, position-NFT
transfer and arbitrary-CPI cases are recorded in
`analysis/daos_fun/REPORT.md`. The live cosigner and closed-wallet exposure
screen is summarized in [`VIRTUAL_XYK_AND_TR2_TR3.md`](VIRTUAL_XYK_AND_TR2_TR3.md).
Our findings are bounded by the pinned snapshots and explicit synthetic
mutations; they neither replace this repository's source audit nor certify
the reconstructed program as safe.
