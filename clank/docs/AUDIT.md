# Security review — AGI on Robinhood Chain

Target: `0xfa31d04462746aaa24bc7e5626403e09e4b106ec` (Artificial Girlfriend Intelligence / AGI), chain ID **4663**. Snapshot: block **96,692,586**, hash `0xd2254f48f5922f7ff13223026dabe708729ed9e187eaf852e3a1343303201c10`, timestamp **2026-10-24 10:22:08 UTC**.

## Result

**No exploitable critical or high-severity defect was confirmed in the selected token.** This is a bounded source review and local execution result, not a guarantee that the token, market, website, or dependencies are risk-free. The review identified one low-severity interface inconsistency and the conditional protocol/compiler risks below. The Solana findings elsewhere in this repository do not apply to this EVM token.

The token uses the **historical** Clank factory `0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1`. Its source differs from the current website factory: AGI explicitly disables burning. Importing the newer, burnable token source would give the wrong behavior and the wrong binary.

At the pinned block, its curve is already `PoolCreated` (enum value 3), the quote asset is native ETH, and the tracked curve reserves are zero. Position NFT **3,034,864** is recorded by and owned by locker `0xe3dc0e862c4eff876a1c40b10205844111da6ee7`. These facts establish the recorded ownership and lifecycle; they do not establish the current market value, depth, or absence of every possible external-protocol failure.

## Scope and method

Reviewed the recovered historical `ClankLauncherToken`, OpenZeppelin ERC-20 implementation and burn extension, `ClankBondingCurve`, `ClankLaunchFactory`, `ClankLaunchDeployer`, `ClankLaunchAndBuy`, `ClankFeeEscrow`, `ClankLaunchLocker`, `ClankGraduationExecutor`, `ClankGraduationGuard`, initialization hook, and curve/migration mathematics. The factory source is [preserved verbatim](../verified/target-factory/sources/contracts/ClankLaunchFactory.sol); the [token](../verified/target-factory/sources/contracts/ClankLauncherToken.sol) and [atomic launch router](../verified/target-launch-forwarder/sources/contracts/ClankLaunchAndBuy.sol) have separate source links.

The first review traced access control, ERC-20 accounting, immutable references, and source/runtime identity. The second review traced lifecycle transitions, custody, rescue, refunds, fee routing, quote assets, and stale trade execution. Both are consolidated here; the second review was not a separate independent auditor's assessment.

Local tests execute the **actual supplied creation bytecode**, not a mocked token. They check exact deployed runtime, constructor metadata and supply, transfer conservation, no token-level transfer tax, unauthorized transfer/burn rejection, authorized burn rejection, failed-call rollback, and absence of the tested mint/upgrade selectors. The transfer property additionally runs 256 fuzz cases. [Test source](../tests/TargetToken.t.sol), [recorded output](../evidence/target-token-tests.txt), [build proof](BUILD.md).

No transactions were sent to Robinhood Chain. Public calls were read-only and pinned. Uniswap V4/Permit2 implementation security, the Safe implementation/modules, frontend signing flows, bridges, private backend code, oracle/market integrity, and all historical launches were not comprehensively audited. A byte-identical rebuild is an identity proof, not a security certification.

## Findings and protocol risks

| ID | Classification | Observation | Applicability to selected AGI |
| --- | --- | --- | --- |
| CL-01 | Low — interface inconsistency | Inherited burn selectors always revert because the token enforces a fixed supply. | Confirmed in the selected token and tested locally. |
| CL-02 | Medium — conditional custody/design risk | Failed swept-launch recovery can send remaining reserves to the factory owner, not token holders. | Not reachable for AGI in its observed `PoolCreated` state. |
| CL-03 | Low — integration risk | Direct curve buy/sell entrypoints have no transaction deadline. | AGI curve trading is already closed; relevant to still-trading launches from this implementation. |
| CL-04 | Informational — governance trust | Fee routing and future-launch settings remain administratively controlled. | Fee-routing authority remains relevant; it is not authority to mint AGI or withdraw its locked position. |
| CL-05 | Informational — external asset assumption | ERC-20 quote-token administration can invalidate accounting/liveness assumptions after approval. | AGI uses native ETH, so this quote-token risk is not present for AGI. |
| CL-06 | Informational — compiler risk, unresolved applicability | Historical solc has published advisories, including an optimized-IR issue. | No target miscompilation reproduced; exact-byte reproduction alone does not rule one out. |

### CL-01 — burn ABI contradicts executable fixed-supply behavior

**Evidence:** `ClankLauncherToken` inherits `ERC20Burnable` but overrides `_update` to revert `FixedSupply()` whenever `to == address(0)`. Consequently both `burn` and `burnFrom` fail even for the holder or an allowance-authorized spender. A revert also restores the allowance spent earlier by `burnFrom`. The local test `testFixedSupplyRejectsEvenAuthorizedBurn` confirms the exact runtime's behavior and rollback.

**Impact:** Integrations that infer burn support from the ABI or parent type can fail at runtime, including workflows that assume supply can be retired. This is not an unauthorized mint, theft path, or hidden transfer tax. Fixed supply appears intentional from the source comments.

**Recommendation:** Describe this deployed token explicitly as fixed-supply and non-burnable in public integrations. For a future deployment, omit the burn extension or expose/document the intentional reversion clearly. Changing the selected source would break faithful reconstruction; no remediation was applied to its recovered code.

### CL-02 — delayed recovery trusts the owner with failed-launch reserves

**Evidence:** `rescueSweptGraduation` requires `onlyOwner`, `Swept` state and seven days since sweeping. It first tries migration with a fixed 5,000,000 gas budget and catches any failure, including out-of-gas. If the retry fails, it marks the launch `Rescued` and sends quote assets and remaining tokens to `owner()`. Its `recipient` argument is only checked for nonzero and does not choose the actual recipient. PoolManager/PositionManager active-callback checks and EIP-150 gas headroom guards are present.

**Impact:** Recovery is not a holder refund mechanism. A legitimate permanent migration failure, or a legitimate migration exceeding the fixed retry budget, leaves reserve disposition dependent on governance. This review did not demonstrate a way for an arbitrary caller to trigger unauthorized recovery, or prove that the normal native migration exceeds the gas cap. Do not describe this as a confirmed permissionless drain.

**Selected-token boundary:** AGI is already `PoolCreated`. The recovery precondition rejects that state, and the locker has no position-transfer, approval, withdrawal, or arbitrary-call entrypoint. The recovery path therefore does not provide a route to AGI's already-locked position under the reviewed code.

**Recommendation:** For future designs, specify holder compensation and treasury custody policy, distinguish permanent failures from insufficient gas, and test the retry gas budget against supported quote assets and external protocol versions. Prefer explicit governance approval and transparent recovery events over an implied holder refund promise.

### CL-03 — direct curve orders have no expiry

**Evidence:** `buy(uint256,uint256,address)` and `sell(uint256,uint256,address)` check minimum output but accept no deadline. An old, still-valid signed transaction may execute later if the state and slippage conditions permit it. The proportional minimum on a terminal partial buy is intentional: the implementation scales the minimum by the gross input actually used.

**Impact:** Minimum output bounds price, not time. Direct callers cannot make an order expire at the curve layer. No bypass of the supplied slippage bound was confirmed. For AGI, the closed curve rejects new curve trades; this finding is not a claim about the separate post-graduation swap router.

**Recommendation:** A future curve entrypoint or trusted execution wrapper should enforce a caller-specified deadline. Integration documentation should distinguish minimum-output protection from expiry and explain terminal partial-fill semantics.

### CL-04 — governance controls persist, with a 3-of-5 owner observed

**Evidence:** The owner can change fee destination, launch gate, configurations for future launches, snipe-tax settings for future launches, trusted launch forwarder, and pair-token authority. Existing curves snapshot economic terms. Already accrued but uncollected factory fee credits follow the current fee destination; the locker also sends collected LP fees to that destination. These powers are separate from user token balances and locked LP principal.

At the pinned block, the owner address `0x77cb92c232137739452446c5712fb0055a344c3d` has proxy code, reports **five owners and threshold three**, and returns implementation `0x29fcb43b46531bca003ddc8fcb67ffe91900c762`. These getter results do not establish that there are no enabled modules, guards, or other execution paths; those were not enumerated. Calling it an EOA or asserting every action requires three signatures would be unsupported.

**Recommendation:** Publish authority and fee-destination policy, monitor configuration changes, and independently review the governance wallet's modules/guards and signer security. Do not market the entire protocol as administratively immutable merely because the token cannot mint and the liquidity NFT cannot be withdrawn through the locker.

### CL-05 — approved ERC-20 quote assets require continuing trust

**Evidence:** Pair-token onboarding checks code, decimals and configured economics. Inbound curve transfers and escrow credits require exact balance deltas. That rejects many fee-on-transfer behaviors, but cannot stop an upgradeable/rebasing/freezable quote asset from changing behavior or disabling transfers later. Outbound transfers use `SafeERC20`, which does not itself guarantee an exact recipient balance delta.

**Impact:** For affected ERC-20-quoted launches, a future asset behavior change could impair trades, migration, recovery or claims. This is a conditional dependency risk, not proof that any currently approved asset is malicious or that AGI loses backing; AGI's quote asset is native ETH.

**Recommendation:** Limit supported quote assets to documented transfer semantics, assess upgrade/freeze/rebase powers, monitor changes, and test transfer rejection and recovery behavior. Removing approval only stops new launches; it does not rewrite existing curve snapshots.

### CL-06 — historical compiler has published bug advisories

The [Solidity bug registry](https://raw.githubusercontent.com/ethereum/solidity/develop/docs/bugs.json), captured on 2026-10-24 in [this evidence file](../evidence/solidity-known-bugs.json), lists six advisories spanning version 0.8.26. SOL-2026-5 requires the non-IR pipeline, which this build does not use. SOL-2026-6 requires named custom-error arguments inside `require`; none were found in the reviewed first-party source. SOL-2026-2 and SOL-2026-4 concern mutual recursion; no such first-party internal call cycle was identified. SOL-2025-1 concerns storage-array slot overflow, not ordinary bounded metadata storage.

**Open applicability:** SOL-2026-7 concerns optimizer bookkeeping and can affect optimized IR even without inline assembly. The target uses that pipeline. No miscompilation was reproduced here, but the local tests do not exclude it. This remains a compiler risk requiring targeted IR analysis/differential testing before a compiler-level assurance claim. Exact reproduction intentionally retains the historical compiler; future remediated deployments should separately assess a fixed compiler and rerun tests. This is not counted as a confirmed exploitable defect in AGI.

## Negative results and retained protections

- The selected token has no owner role, external mint entrypoint, pause/blacklist logic, fee-taking transfer hook, delegatecall proxy fallback, or upgrade entrypoint in its recovered implementation. Immutable `deployer`, `curve` and `launchFactory` references are informational; they do not grant token mint or confiscation powers.
- All initial tokens are minted to the constructor-specified curve. ERC-20 transfers consume balances and finite allowances; unauthorized movement and supply conservation are tested. The fixed-supply hook disallows burns after deployment.
- Curve pricing uses tracked reserves rather than raw ETH balances. Forced ETH and direct token donations do not change those pricing variables. State-changing trade entrypoints are reentrancy guarded; the factory-only curve sweep uses state-before-transfer transitions.
- Token/curve initialization and lifecycle calls are restricted; CREATE2 inputs bind creator, metadata and economics. Zero `expectedEconomics` deliberately waives the commitment in the compatibility entrypoint, so clients wanting pinned terms must supply a nonzero expected hash.
- The initialization-only hook requires the configured PoolManager and wired factory, preventing ordinary third-party pre-initialization of that hook's pool. It does not run on swaps or impose a swap tax.
- Graduation mints the position to the permanent locker, verifies NFT ownership and clears temporary approvals. The locker removes zero liquidity when collecting fees and has no withdrawal path in the reviewed source.
- Fee claims debit the caller's own credit before external transfer and use reentrancy guards. The beneficiary, not an arbitrary caller, selects a claim recipient. The atomic launch router forwards the original caller's identity and measures refunds relative to a pre-call balance baseline.

These observations are source-level checks unless a local test or pinned-state call is explicitly cited. They are not a claim that every interleaving or external dependency was exhaustively tested.

## Recommended priorities

1. Publish the exact historical AGI source and its fixed-supply/non-burnable behavior alongside the bytecode evidence.
2. Keep the target token, its historical factory, and the site's newer factory separate in monitoring and documentation.
3. Document the failed-launch custody policy and continuing fee/governance authority.
4. Add deadline enforcement to future direct-curve execution interfaces and test supported quote assets and migration gas limits.
5. Extend a separate review to the post-graduation swap path, Uniswap/Permit2 deployments, frontend signing and governance wallet configuration before claiming a full-system audit.
