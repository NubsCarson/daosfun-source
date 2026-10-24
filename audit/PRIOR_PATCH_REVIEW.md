# Review of the earlier remediation experiment

Date: 2026-10-24. This is a review of an earlier, separate patch experiment. The
source in this repository is the byte-identical recovery and **does not contain
these fixes**. The earlier patch is not a deployment recommendation or a claim
that the program is now secure.

## Historical test evidence

The earlier patch build was labeled `security-fixes-v3`, with a 1,058,144-byte ELF
and SHA-256 `a8fe1353af4f21ef4ab5b34d5c14f6a0506a3b39e2b1bc831c8a19f4b461f562`.
Its recorded tests reported 26/26 targeted checks and 14/14 unexpired-execution
regression checks. In the 410-case differential suite, seven execution cases
changed because expiry was newly enforced and three redemption-init cases changed
because expiry and Token-2022 behavior changed. Those results establish only the
tested behaviors, not comprehensive remediation. The historical patched executable
is not the matching binary in `binaries/`.

## Changes attempted and present assessment

| Finding | Earlier change | Assessment |
| --- | --- | --- |
| BM-1 | Derive the DBC pool from the pinned config and this DAO's mint pair. | Addresses the tested cross-pool substitution. Revalidate against the dependency version used for any proposed upgrade. |
| TR-1 | Stop execution at `expiration_timestamp`; let redemption open at expiry without privileged close. | Addresses the tested expiry gate, but changes policy for every already-expired live DAO. |
| TR-2 | Remove the cosigner's signer flag from CPI metas and cloned account infos. | Addresses the tested direct forwarding of that signer. Other outer signers remain forwarded. |
| TR-3 | Reject direct SPL Approve/ApproveChecked/authority installation; allow authority removal after close; reject unsafe treasury delegate/native-close-authority states during redemption. | **Incomplete as a general prevention mechanism.** The first-hop instruction filter does not cover a nested CPI through another program. |
| TR-4 | Change redemption-init token program from legacy `Program<Token>` to `Interface<TokenInterface>`. | Addresses the tested basic Token-2022 mint mismatch. This does not establish safety for every Token-2022 extension. |
| BM-2 | Add a pool PDA binding in the fee-claim path. | Defense in depth for a refuted exploit hypothesis, not an additional confirmed vulnerability. |

## Additional source-level concern: nested CPI bypass of TR-3 filtering

The earlier patch's open-fund execution path only inspects approval opcodes when
`instruction_program` equals SPL Token or Token-2022. It otherwise permits an
arbitrary target and forwards the treasury wallet PDA's signer privilege.
A forwarding program can receive that signer privilege and invoke the token
program itself. Such a nested approval does not pass through the patch's direct
opcode filter.

This conclusion follows from inspecting the earlier patched
`handle_execute_invoke` source. It has **not** been reproduced against the
historical patched binary in this review, so it is recorded as a source-level
remediation gap rather than a new independently confirmed original-binary finding.
It retains TR-3's admin/delegate-plus-platform-cosigner preconditions; it is not an
unauthenticated takeover.

A durable design needs an authorization policy that covers the full effects of
execution. Options include narrowly audited adapters instead of unrestricted CPI,
and post-CPI checks on all relevant writable treasury token accounts. A small
first-instruction opcode blacklist is insufficient. Any solution must also account
for privileges already installed before an upgrade and for mint-level authorities.

## Remaining design questions

- Delegates already installed before closure need a usable revocation path. An
  owner cannot remove a close authority controlled by another key merely by calling
  `SetAuthority`; SPL Token checks the current authority.
- A close authority on a wrapped-SOL account can take the account's lamports.
  A close authority on an ordinary non-native token account cannot close it while
  it still has a positive token balance. Treating these identically can add a
  redemption denial of service.
- Lazy per-asset snapshots remain unchanged in the earlier patch. Later deposits,
  depletions, rounding and SOL rent must have explicit settlement rules. See
  [the security audit](AUDIT.md).
- A live-balance cap by itself is not a fairness solution: it can pay early
  redeemers in full and leave later redeemers with the loss.
- Blocking arbitrary approvals can break legitimate DeFi integrations. The
  protocol's intended permission model must be decided before replacing it.
- Token-2022 transfer fees, hooks, permanent delegates, mint/freeze authorities,
  and account closure semantics require their own compatibility review.
- The captured DAMM dependency rejects the recovered older fee-parameter encoding
  on some migration paths. Binary fidelity deliberately preserves that behavior;
  upgrading dependency interfaces is a separate, behavior-changing project.

No patch from this experiment has been deployed by this recovery task.
