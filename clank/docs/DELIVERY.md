# Recovery delivery record

The AGI target, its historical factory and seven first-party dependencies, its curve, and seven separately captured current-website contracts have locally reproduced runtime binaries. All **17 runtime pairs** are byte identical. The selected token's entire **8,058-byte creation payload** also matches, including the original ABI constructor arguments.

Local verification:

- Official solc 0.8.26 WASM artifact SHA-256 verified before compilation.
- Original materialized sources compared to archived compiler inputs.
- Whole-runtime comparisons retain metadata and allow only compiler-declared immutable substitutions.
- Seven tests execute the supplied original token initcode/runtime in a local Foundry EVM, including 256 fuzz transfer cases; all passed.
- The local test harness used native solc 0.8.28 and Foundry 1.7.1. It does not compile or substitute token code: it deploys the supplied creation bytes. The exact recovery compilation separately uses solc 0.8.26.
- Negative verifier checks reject a changed capture byte, changed compiler output byte, and undeclared immutable value ([results](../evidence/verification-negative-tests.json)).
- The repository's original Solana release verifier still passes: 70 source/config files and the padded 1,120,784-byte binary remain unchanged.

The consolidated [audit](AUDIT.md) distinguishes a low-severity burn-interface inconsistency from conditional custody, integration, governance, quote-asset and compiler risks. No critical/high token exploit was confirmed. Compiler-advisory applicability is not fully resolved, and the external market/router/bridge/governance implementation scope is explicitly limited.

No live transactions, wallet connections, deployment, or remediation were performed. The recovered source intentionally preserves deployed behavior.
