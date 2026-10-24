# Security audit — AGI / clank.trade

## Scope

**Target:** AGI (`0xfa31d04462746aaa24bc7e5626403e09e4b106ec`) on Robinhood Chain, chain ID **4663**, and its associated Clank launch contracts.

**Factory:** `0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1`. This is distinct from the factory currently advertised by clank.trade. The reviewed source reproduces AGI's creation payload and deployed runtime byte for byte. [Build evidence](BUILD.md).

**State snapshot:** block **96,709,714**, hash `0x8544aa36fb7ae4fd24e8ba8257de59e66f4799fe81bc9621bd279581ac8b24d7`, **October 24, 2026, 03:52:53 PDT**. The token, curve and factory runtime hashes match the original captures. [State evidence](../evidence/audit-state-refresh.json).

The scope includes the historical token, OpenZeppelin ERC-20 implementation, bonding curve, launch factory, deployer, atomic launch router, fee escrow, liquidity locker, graduation executor, graduation guard, initialization hook, and curve/migration mathematics. Sources: [factory and dependencies](../verified/target-factory/sources/contracts/), [atomic launch router](../verified/target-launch-forwarder/sources/contracts/ClankLaunchAndBuy.sol).

AGI's curve is in `PoolCreated` state, uses native ETH as its quote asset, and has zero tracked reserves. Position NFT **3,034,864** is recorded by and owned by locker `0xe3dc0e862c4eff876a1c40b10205844111da6ee7`. These observations establish lifecycle and custody, not market value or liquidity depth.

## Summary

**No CRITICAL or HIGH finding was confirmed.** Two findings meet the reporting threshold: one **MEDIUM** conditional custody risk and one **LOW** execution risk. Neither provides an active exploitation path against AGI's already-graduated curve in the captured state.

| Severity | Count |
| --- | ---: |
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 1 |

| ID | Severity | Finding | Applicability to AGI |
| --- | --- | --- | --- |
| CL-02 | MEDIUM | Failed-launch recovery transfers reserves to the owner without a holder refund mechanism | Recovery requires `Swept`; AGI is already `PoolCreated`. |
| CL-03 | LOW | Direct curve orders have no execution deadline | AGI's curve is closed; relevant to still-trading launches using this implementation. |

## CL-02 — MEDIUM: Failed-launch recovery transfers reserves to the owner

**Location:** [ClankLaunchFactory.sol:855](../verified/target-factory/sources/contracts/ClankLaunchFactory.sol#L855), `rescueSweptGraduation`.

**Preconditions:** The caller is the factory owner, the launch is in `Swept` state, at least seven days have elapsed since sweeping, and the migration retry fails.

**Evidence:** The function attempts migration with a fixed 5,000,000 gas budget. It catches any failure, including out-of-gas, marks the launch `Rescued`, and transfers the remaining quote assets and tokens to `owner()`. The `recipient` argument is checked for nonzero but does not select the actual recipient. PoolManager/PositionManager callback-state checks and EIP-150 gas-headroom guards are present.

**Impact:** Recovery gives governance custody of failed-launch reserves without an on-chain mechanism to reimburse token holders. A permanent migration failure—or migration that exceeds the fixed retry budget—can leave holders dependent on the owner's subsequent disposition of those assets. The MEDIUM rating reflects this conditional custody risk; it is not a confirmed permissionless drain or proof that ordinary migration exceeds the gas cap.

**AGI applicability:** The captured AGI state is `PoolCreated`, which fails the recovery precondition. A local replay impersonating the legitimate owner and advancing time by one year confirms that both rescue and force-sweep reject that state. The reviewed locker exposes no withdrawal, approval, transfer, or arbitrary-call entrypoint for its position NFT.

**Recommendation:** Define and implement a holder-compensation mechanism for failed launches. Separate permanent migration failures from insufficient execution gas, test retry budgets against supported dependencies, and make reserve disposition explicit in governance policy and events.

## CL-03 — LOW: Direct curve orders have no execution deadline

**Locations:** [ClankBondingCurve.sol:324](../verified/target-factory/sources/contracts/ClankBondingCurve.sol#L324), `buy`; [ClankBondingCurve.sol:374](../verified/target-factory/sources/contracts/ClankBondingCurve.sol#L374), `sell`.

**Preconditions:** The curve remains in `Trading` state and an older signed transaction is still valid and satisfies the supplied minimum-output condition.

**Evidence:** Both entrypoints enforce minimum output but accept no deadline. The terminal partial-buy path scales the minimum proportionally to the gross input actually consumed.

**Impact:** An order can execute after the user's intended time window. Slippage protection bounds output relative to the submitted order; it does not provide expiration. No bypass of the supplied slippage bound was confirmed.

**AGI applicability:** AGI's completed curve rejects further curve trades. This finding does not assess the separate post-graduation swap router.

**Recommendation:** Add a caller-specified deadline to future curve entrypoints or an execution wrapper that enforces it. Document expiration and terminal partial-fill semantics separately from minimum-output protection.

## Verification

**28 tests passed:** 13 token tests, four native fee-escrow tests, and 11 captured-state authorization/lifecycle tests. Four token properties each run 1,024 cases (**4,096 fuzz cases**); the transfer-sequence property performs **32,768 modeled transfer steps**.

| Area | Checks | Result |
| --- | --- | --- |
| Source and deployment identity | Entire creation payload, deployed runtime, constructor values and CREATE2 address | Matched captured AGI evidence. |
| Token balances and supply | Transfers, self-transfers, finite/infinite allowances, overspending, zero-recipient rollback and transfer sequences | No unauthorized movement, supply inflation or model divergence reproduced. |
| Token authority | Mint/upgrade selectors and burn behavior | No external mint or upgrade path found; fixed-supply burn rejection confirmed. |
| Native fee escrow | Cross-beneficiary claims, reentrant claims, rejected-payment rollback and forced-surplus accounting | Tested theft and accounting-failure hypotheses rejected. |
| Curve and factory authorization | Direct sweeps, reinitialization, lifecycle changes and owner-only rescue across explicit caller roles | Expected authorization guards enforced. |
| Completed-launch recovery | Owner rescue and force-sweep after a one-year local time advance | Completed lifecycle state rejected. |
| Helper functions and repeated graduation | Direct retry-helper calls, repeat sweep and pool creation | Self-call and lifecycle guards enforced. |
| Graduation executor | Unauthorized migration call | Rejected before reserve movement. |
| Liquidity custody | Locker reassignment, approval attempt and direct NFT transfer | Rejected; NFT ownership remained with the locker. |
| Initialization hook | Forged caller and forged factory sender | PoolManager and factory checks enforced. |

[Token tests](../tests/TargetToken.t.sol), [escrow tests](../tests/FeeEscrowAudit.t.sol), [authorization/lifecycle tests](../critical-tests/CriticalPaths.t.sol), [token and escrow results](../evidence/security-audit-tests.txt), [captured-state results](../evidence/critical-pass-tests.txt).

The token and escrow tests deploy captured original initcode. The authorization/lifecycle tests replay a partial snapshot of **nine accounts and ten storage slots** and verify six contract runtimes against their captures. After each tested action, storage-read instrumentation rejects uncaptured-slot reads in the included accounts. This is not a full chain-state dump or a Merkle-proof verification. [Snapshot](../evidence/critical-snapshot/snapshot.json).

```sh
forge test --root clank/tests --use 0.8.26 --fuzz-runs 1024 -vv
forge test --root clank/critical-tests --use 0.8.26 -vv
python3 clank/scripts/verify_package.py
```

Recorded local runs use solc 0.8.28 for test harnesses; CI uses 0.8.26. The production bytecode executed by the tests remains the captured original code. No live transactions or deployments were performed.

## Limitations

This audit does not establish the absence of all vulnerabilities. Full implementation audits of Uniswap V4/Permit2, the governance wallet, post-graduation swap routing, bridges, frontend signing flows and private backend code are outside scope. ERC-20 quote-asset behavior is source-reviewed rather than covered by the native-escrow tests. Compiler-advisory applicability has not been exhaustively resolved; byte-identical reproduction does not exclude miscompilation.

The randomized network-backed fork run was rate-limited and is excluded from successful test counts. The completed captured-state tests use explicit caller roles. Results apply to the identified implementation and captured state, not future configurations or every historical launch.
