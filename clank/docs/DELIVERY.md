# Recovery delivery record

The AGI target, its historical factory and seven first-party dependencies, its curve, and seven separately captured current-website contracts have locally reproduced runtime binaries. All **17 runtime pairs** are byte identical. The selected token's entire **8,058-byte creation payload** also matches, including the original ABI constructor arguments.

Local verification:

- Official solc 0.8.26 WASM artifact SHA-256 verified before compilation.
- Original materialized sources compared to archived compiler inputs.
- Whole-runtime comparisons retain metadata and allow only compiler-declared immutable substitutions.
- Thirteen token tests and four native fee-escrow tests execute captured original initcode/runtime in a local Foundry EVM, including 4,096 fuzz cases; all passed.
- Eleven authorization/lifecycle tests replay nine captured accounts and ten storage slots. All passed; reads of uncaptured storage slots in the included accounts are rejected. [Results](../evidence/critical-pass-tests.txt).
- The local test harness used native solc 0.8.28 and Foundry 1.7.1. It does not compile or substitute token code: it deploys the supplied creation bytes. The exact recovery compilation separately uses solc 0.8.26.
- Negative verifier checks reject a changed capture byte, changed compiler output byte, and undeclared immutable value ([results](../evidence/verification-negative-tests.json)).
- The repository's original Solana release verifier still passes: 70 source/config files and the padded 1,120,784-byte binary remain unchanged.

The [audit](AUDIT.md) reports one MEDIUM conditional custody finding and one LOW execution finding. No CRITICAL or HIGH finding was confirmed. Scope and applicability limits are stated with the findings.

No live transactions, wallet connections, deployment, or remediation were performed. The recovered source intentionally preserves deployed behavior.

## Published source and hosted verification

The source, original artifacts, comparison binaries and audit were published to [lalalune/daosfun-source](https://github.com/lalalune/daosfun-source) in commit [`d8a4dd5d144cc8c5c4bd20ae1a54e66525a50c5e`](https://github.com/lalalune/daosfun-source/commit/d8a4dd5d144cc8c5c4bd20ae1a54e66525a50c5e).

- [Initial hosted Clank run](https://github.com/lalalune/daosfun-source/actions/runs/40085892678): independently reproduced all 17 runtimes, then caught stale input-hash metadata in an earlier local build report. It stopped at the post-build package-integrity check before executing the token tests. The reports were regenerated using the final compiler wrapper; binary bytes did not change.
- [Latest Clank verification runs](https://github.com/lalalune/daosfun-source/actions/workflows/clank.yml?query=branch%3Amain): the complete workflow rebuilds all contracts, checks package integrity before and after compilation, and executes the original token bytecode locally. Each run identifies its exact commit and terminal result.
- [Original Solana regression run](https://github.com/lalalune/daosfun-source/actions/runs/40085892651): passed on the same published source commit.

The links above identify the exact tested source commit. Subsequent report-metadata and documentation edits do not change its recovered sources or binary bytes. Consult the linked run's terminal status for hosted completion; the local results above are separate evidence.
