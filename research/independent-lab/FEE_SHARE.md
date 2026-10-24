# FeeShareTraderDAO: layout, payout, and legacy authority

The pinned current FeeShareTraderDAO executable is
`Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk`, SHA-256
`88df1b4ddb152d4159b41b9eba68ab74e6f0e14c1930bad5828c44a14a3ca4f8`
(last deployment slot 364247116). The nine site-IDL handlers each have a
bounded local success; full behavior remains open.

The 169-byte FeeShare state contains a Borsh `Option<Pubkey>` referrer. When
the tag is `None`, fee counters begin at **byte 113**; when it is `Some`, they
begin at **byte 145**. Treating the `None` layout as a fixed 145-byte prefix
creates false zero-counter readings. A captured no-referrer account instead
shows creator and platform payouts of **809,340,185,180** funding units each,
with one unit in its vault. A historical transaction paid 475,188,415 units
to each of two recipients. Twenty local payout/guard cases, with signer
metadata modeled under disabled signature verification, conserve vault,
recipient, and counter changes in the tested layouts. This corrects a parser
artifact; it is not an unpaid-fee
finding. See the [Option-layout matrix](receipts/fee-share-redeem-option-layout-matrix.json)
(`analysis/daos_fun/fee-share-redeem-option-layout-matrix.json`).

The [signed payout lifecycle](receipts/fee-share-signed-payout-lifecycle.json)
adds **27 validly signed, committed local sends** against the exact current
FeeShare ELF. It uses the two captured State/vault layouts plus a locally
distinct-referrer variant. Creator and referrer keys are replaced with
disposable signing keys and canonical recipient ATAs; the exhausted
no-referrer account receives 1,000 synthetic fee/vault units. The signed
creator receives its exact 500-unit cap there and 8,922,753,598 units on
each referrer layout; vault and `creator_distributed` deltas reconcile.
A signed third-party fee payer then collects the no-referrer platform's
remaining 500 units, leaving the original one-unit vault balance. Signed
outsider/referrer and tested entity 1/2 redemption attempts fail 6001;
over-cap and repeat claims fail 6002 without changing tracked protocol
accounts. Pinned BPF instructions independently show the nonzero-entity
authorization branch and 50/100 cap path. The distinct referrer and fee
accrual are local constructions; no real referrer entitlement, live payout,
or fund-loss finding follows.

The [writable offline Surfpool lifecycle](receipts/fee-share-signed-surfpool-stateful.json)
commits **24 validly signed local transactions** against the pinned current
ELF across `None` and `Some` referrer layouts. Creator and platform payouts
reconcile with vault and distributed-counter deltas; wrong-signer,
over-cap, and repeat controls leave tracked protocol accounts unchanged.
Creator/referrer keys, recipient ATAs, and fee accrual are explicitly local
substitutions, so this is a stateful payout check rather than a live claim.

The bundle also includes `reconstruction/fee-share-redeem/`, a newly written
**native Rust model** of the 169-byte State `Option<Pubkey>` layout and the
tested creator `redeem(entity=0)` and `collect_platform_fees` accounting
branches. Its [differential receipt](receipts/fee-share-redeem-rust-differential.json)
matches **96/96** validly signed local calls against the unmodified current
FeeShare ELF: 59 successes and 37 expected failures across captured account
layouts with explicit synthetic creator/referrer keys, ATAs, and positive
accrual. The model omits Anchor account constraints, vault/ATA checks, SPL
Token CPI, other entity semantics, and fee accrual. It is not original source,
an SBF build, byte-identical reconstruction, or a full handler proof.

The tested `redeem` creator cap is `floor(total_fees/2) −
creator_distributed`. Cap+1 and altered owner/program/account cases reject.
`collect_platform_fees`, `claim_meteora_fees`, `claim_raydium_fees`, and
`claim_meteora_dbc_fees` execute on pinned local snapshots. The tested claim
handlers allow a different caller to trigger the claim while their recipient
and protocol-account guards remain in force; permissionless triggering is
not evidence of permissionless redirection. A sampled Raydium claim then
token sale conserves its token/funding deltas when the local Clock matches
the historical transaction. See the corresponding `fee-share-*.json`
receipts and `analysis/daos_fun/REPORT.md` in the bundle.

An older, distinct FeeShare program controls 168-byte fee states through
legacy PDAs. A successful historical `CurveWithdraw` made that program's PDA
an inner CPI signer to VirtualXYK `RedeemFees`; a later-state signed local
replay moves exactly the requested funding units up to the stored fee cap.
Current FeeShare cannot sign the legacy program's PDA. This identifies an
authorized legacy fee route, not an outsider fee drain. See
`analysis/daos_fun/legacy-curve-withdraw-authority-path.json` and
`analysis/root_virtual_xyk/signed-active-legacy-redeem.json`.

Historical initialization of eight newer 169-byte states from old 168-byte
accounts matches eight rent balances and surviving headers, but the source
transaction predates the current FeeShare deployment and exact source-slot
program bytes are not available. The distinction between source-era and
current binaries is recorded in `fee-share-legacy-eight-replay.json`.
