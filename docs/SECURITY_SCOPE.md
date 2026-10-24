# Security review scope and evidence

Reviewed 2026-10-24. Target: `4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM`.
The review covers the captured executable and its faithful reconstructed DAO
program. It does not certify the current mainnet state, external protocols,
cosigning service, front end, or upgrade operators.

The 1,041,728-byte reconstructed ELF matches the captured ELF. Adding 79,056 zero
allocation bytes gives the full-file hash
`5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`.
See [reproduction](BUILD.md) and [proof](../repro/final-proof.json). Source-level
observations can therefore be related to the matching binary, but binary identity
alone does not prove a security claim or validate assumptions about other actors.

## Findings and confidence

- [Security audit](../audit/AUDIT.md): six findings reproduced against the captured
  original—one critical, four medium, and one low. The low-severity snapshot finding
  is supported by signed local transactions and a control. The SOL rent-remainder
  failure hypothesis was not reproduced in the tested VM and is not counted as a
  finding. The original vulnerabilities are intentionally retained in this source.
- [Prior remediation review](../audit/PRIOR_PATCH_REVIEW.md): a historical patch
  experiment is not part of this faithful build. Its direct token-opcode filter
  does not establish protection against nested CPI effects.

`CONFIRMED_ON_ORIGINAL` means a bounded local execution reproduced the stated
behavior using the captured original program. It does not mean a real-world attack
occurred. `Source-level concern` means code reasoning without a dedicated runtime
reproduction in this review. An unconfirmed concern is not counted as a confirmed
vulnerability. A refuted hypothesis is not a low-severity vulnerability.

## Source review: all 18 entrypoints

This matrix records source review of the creation, authorization and migration
surfaces, with redemption runtime cases described in the unified security audit. A checked constraint is not an assertion of universal safety.

| Entrypoint | Checks and effects reviewed | Result / remaining boundary |
| --- | --- | --- |
| `initialize` | Fresh mint/state initialization; state PDA; fee-share creator, funding mint and DAO mint binding; metadata authority; fixed issuance; carry cap of 4,000 basis points. | No additional authorization bypass identified. Funding goal and duration are creator parameters; zero/extreme configurations and funding-mint authorities remain integration concerns. |
| `init_bonding_on_meteora` | Fresh state and mint signer; pinned DBC config/program; fee-share identities; global creator PDA; metadata authority handoff. | No additional creation-state overwrite identified. External DBC validates pool creation; the shared signer makes missing bindings in later calls security-sensitive. |
| `start_raise` | Admin signer; both mint identities; uninitialized-curve condition; seven-day upper bound; fixed token allocation and initial commitment. | No new bypass identified. Repeat initialization is delegated to the pinned fundraise program; failure must remain atomic. |
| `init_curve` | Admin or hard-coded operator; finalized fundraise PDA; state/mint bindings; token-account ownership; fixed pool parameters; transfer destinations; permanent position lock. | No new unauthorized withdrawal identified. Amounts use the configured goal, not arbitrary excess deposits. Handling excess funds and zero/extreme goals remains a design concern, not a confirmed theft. |
| `migrate_bonding_to_meteora` | State and hedgefun curve PDA/mints; pinned programs/config; destination ATAs; fixed token allocation; funding reserve; position NFT destination. | Permissionless payer alone is not a bypass: the curve must belong to the state and the external migration must succeed. Legacy availability and DAMM interface compatibility remain dependencies. |
| `finalize_meteora_bonding` | Quote vault and state checks; global signer; untyped caller-supplied pool; unconditional lifecycle writes after CPI. | Confirms BM-1's missing DAO-to-pool binding; no second issue is counted for the same root cause. |
| `claim_dbc_trading_fees` | Fee-share PDA signer, mint identities, fixed recipients, before/after balance deltas and external DBC checks. | The missing local pool binding alone is not a confirmed exploit; BM-2 remains refuted within the tested assumptions. |
| `transfer_position_nft_to_fee_share` | Typed pool and position owners; both pool mints; position-to-pool identity; NFT PDA; derived fee authority recipient. | No new arbitrary NFT destination identified. Permissionless triggering does not make the recipient attacker-selected. |
| `add_delegate_authority` | State/mint PDA; admin signer; three-entry capacity; duplicate rejection. | No delegate-to-admin escalation identified. A later error rolls back earlier writes in the same transaction. |
| `revoke_delegate_authority` | Same admin checks; exact key removal. | No new bypass identified. Revocation cannot undo independent authorities already granted to external token programs (TR-3). |
| `execute_invoke` | Admin/delegate membership, global cosigner PDA, wallet PDA signature, unrestricted target and remaining-account privileges. | TR-1/2/3 remain. The cosigner's off-chain policy is not observable from this source. |
| `close_fund` | Hard-coded close authority and matching state/mint PDA; one-way flag. | No unprivileged close path identified. Closure changes a DAO flag only; it does not neutralize external authorities. |
| `cosign_init` | Hard-coded admin; fresh `[cosigner, id]` PDA. | No unprivileged initialization identified. Execution specifically uses id zero. |
| `cosign_update_signer` | Hard-coded admin; typed, program-owned state. | No unprivileged signer update identified. Missing PDA validation here does not let an outsider choose execution's cosigner, because execution pins the canonical id-zero PDA. |
| `init_redemption` | Matching state/mints; curve-initialized gate; one-time activation; privileged-close condition; capped carry to state admin. | TR-1/4 remain. Activation does not snapshot all treasury assets or revoke delegates. |
| `burn_dao_tokens` | Redemption-started state; signer-owned ATA and state ATA; checked accumulation. | This escrows tokens rather than burning mint supply. Zero amount can establish a zero-credit metadata account, relevant to TR-5 snapshot tests. |
| `redeem_sol` | User metadata and wallet PDA; per-user claim accumulator; lazy global SOL snapshot; payout formula. | See TR-5 and the negative rent-remainder result in the audit. There is no direct clock gate here; credit provenance supplies the lifecycle dependency. |
| `redeem_tokens` | Mint/owner/program checks; signer ATA; per-source snapshot and per-user accumulator. | TR-3 remains. See TR-5 zero-amount and later-deposit behavior. Token-2022 extension semantics are not fully covered. |

## Unconfirmed and integration concerns

1. **Excess state-vault deposits.** `init_curve` transfers the configured funding
   goal in pool and reserve portions. There is no general state-vault sweep in the
   reviewed DAO handlers. Whether an external raise can create recoverable excess
   balances needs an end-to-end fundraise review; do not label this confirmed theft.
2. **Zero and extreme parameters.** Pool math contains explicit panics and checked
   arithmetic. Creator-selected zero funding and extreme ratios can make a
   lifecycle path fail. No cross-DAO exploit or wrapped arithmetic gain was shown.
3. **External mint controls.** Funding mints are not restricted to an approved
   set. Freeze, permanent-delegate, transfer-fee and hook behavior can change the
   safety of deposits and settlement. Accepting such mints requires an explicit
   product policy and separate extension tests.
4. **Dependency evolution.** A captured external program is a versioned assumption.
   A future upgrade can invalidate account layouts or fee-parameter compatibility;
   the DAO's exact reconstruction does not imply live integration compatibility.
5. **Operator concentration.** Hard-coded close/operator keys and the global
   cosigner are privileged by design. Key compromise and off-chain approval rules
   are outside the local binary tests.

## Test limitations

Public-account fixtures sometimes bypass cryptographic signature verification to
exercise authorization branches without private keys. They still pass explicit
signer flags through the runtime and execute the program checks. Synthetic
balances and state setup isolate behavior; they are not evidence that the same
state or asset exposure exists on mainnet. Original-binary PoCs, exact comparison,
and differential tests answer different questions and are reported separately.

No mainnet transaction, exploit broadcast, deployment or key operation was performed.
The review is not a formal proof or an exhaustive professional audit.
