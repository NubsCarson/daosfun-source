# Clank source recovery and runtime reproducibility

The user-specified AGI token at `0xfa31d04462746aaa24bc7e5626403e09e4b106ec` reproduces **byte-for-byte** from recovered Solidity sources: its 3,139-byte runtime and the entire 8,058-byte supplied creation payload match. Its curve also reproduces at runtime. The creation payload consists of 7,066 bytes of locally compiled initcode and 992 bytes of the original ABI-encoded constructor arguments.

The token belongs to historical factory `0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1`, which differs from the factory currently advertised by the website, `0x798daaa0707c1e538bb5acf0867ac0e1a84cccf2`. **Their token source differs:** the historical token rejects burns to preserve fixed supply. All are EVM contracts on Robinhood Chain, chain ID **4663**, rather than the Solana program at the repository root.

Historical source was recovered from the [verified target factory](https://sourcify.dev/server/v2/contract/4663/0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1?fields=all). Although the token itself did not have a direct Sourcify record at capture time, the historical factory compilation input includes its exact token and curve source, and independent local compilation matches both deployed runtimes including their metadata. The website's current factory source was recovered separately from its [Sourcify record](https://sourcify.dev/server/v2/contract/4663/0x798daAa0707C1e538bB5Acf0867Ac0e1A84cccF2?fields=all).

Each verified deployment retains its own original source-unit paths and source text under `verified/<name>/sources/`. The target token and curve use `verified/target-factory/sources/`. No source-code decompilation guesses or modifications are needed for these matched contracts.

## Compiler and build settings

- Compiler: `0.8.26+commit.8a97fa7a.Emscripten.clang`.
- Official compiler artifact: [`soljson-v0.8.26+commit.8a97fa7a.js`](https://binaries.soliditylang.org/wasm/soljson-v0.8.26+commit.8a97fa7a.js).
- Compiler artifact SHA-256: `db85e5396f523cc1a53c4c4d742e204f6dcba1a05842623d73be946809e11cd6`.
- Factory settings: optimizer enabled, 200 runs; `viaIR: true`; EVM target `cancun`; IPFS metadata hash with appended CBOR; original source paths, remappings, and dependency contents preserved.
- The scripts use the exact individual contract settings from each archived Standard JSON input. They add only `outputSelection` to request compiler artifacts. They do not resolve packages or substitute newer dependencies.

The dependency source contents are captured exactly. A dependency package version is not claimed solely from its contents or a source-file comment; exact source text is sufficient for this byte-level reproduction, while reconstructing an original package-manager lockfile is a separate question.

## Reproduce

From the repository root, with Python 3, Node.js and curl available:

```sh
# Primary target: AGI token creation payload, token runtime, and curve runtime.
python3 clank/scripts/rebuild_target.py

# Historical target factory and its dependencies.
python3 clank/scripts/rebuild.py target-factory target-fee-escrow target-locker target-graduation-executor target-graduation-guard target-initialization-hook target-launch-deployer target-launch-forwarder

# Separate contracts currently advertised by the website.
python3 clank/scripts/rebuild.py factory fee-escrow locker graduation-executor graduation-guard initialization-hook launch-deployer
```

The command downloads the compiler only if absent and verifies its pinned SHA-256 before loading it. It compares every materialized source file with its archived verified source, compiles that materialized text locally, and writes local compiler output under ignored `clank/.build/`. Downloaded compiler files remain under ignored `clank/.cache/`.

For deployments with a direct verified record, the verifier checks all of the following:

1. The raw local compiler runtime equals the complete Sourcify recompiled runtime.
2. The RPC-captured runtime equals the complete Sourcify on-chain runtime.
3. The immutable-reference ranges emitted by the local compiler equal the published reference ranges.
4. Deployment-specific immutable values are inserted only into those compiler-declared, initially zero-filled ranges. Missing values, extra values, overlapping ranges, and linked-library references are rejected.
5. The entire resulting runtime equals the RPC capture, with no ignored bytes, metadata stripping, arbitrary patches, or normalized comparison.

Solidity immutables are populated by constructor execution at deployment, so the uninstantiated compiler runtime is not itself the deployed runtime. The records in `evidence/build/` list every immutable value and offset applied. Their values come from the public verification record and are corroborated by the independent runtime capture. This process proves source/runtime identity with those deployment constants; it does not independently execute the original constructor or prove historical storage initialization.

For the target token, `verify_target.py` instead compares the local initcode with the exact prefix of the user-supplied creation payload, decodes the three address immutables from the original constructor-argument suffix, checks them against captured public getters, and compares the full instantiated runtime against both the supplied runtime and RPC capture. It writes the entire rebuilt creation payload to `binaries/target-token.creation.bin`. The 992 constructor bytes are captured inputs, not values inferred from decompilation.

For the target curve, the same script restricts substitutions to local compiler-declared immutable ranges, requires each repeated immutable value to agree across all its sites, and corroborates available public getter values. These curve constants are extracted from the runtime capture; the curve constructor is not independently reconstructed by this script. Every other byte, including metadata, must match. Separate local constructor-execution tests for the supplied token are recorded in the target test evidence.

Each `binaries/<name>.runtime.bin` is the locally compiled runtime after these immutable substitutions. Each `evidence/contracts/<name>.runtime.bin` is the independently captured comparison artifact. No changes are deployed on-chain.

## Verified target runtime results

| Contract | Runtime bytes | SHA-256, identical capture and rebuild |
| --- | ---: | --- |
| `target-token` | 3,139 | `190f2abee01041531efc2c2618d8f7f1b1ae8ba9bb183e42f786982b4e4bf155` |
| `target-curve` | 8,639 | `aeab07d54092e288ba40023f0edba6c981250e65c4d805845f0102338ba9a860` |
| `target-factory` | 23,095 | `5d8656bf73f4e4dbd656bdc9be353b6db6556acece4936dc5b42d5db9f941bfb` |
| `target-fee-escrow` | 1,969 | `ecfda94a9a6445f932bdc2774f689c676be80a6fb4d5f490c0b07ddb54d27ac2` |
| `target-locker` | 2,570 | `11573ee99f172b6112827b08850b40c5218e4205b06a04603c96f571c11204d0` |
| `target-graduation-executor` | 9,195 | `6124909bf743016481110e1b5a93c94113691150aa01a2bb01effb99a7bd544d` |
| `target-graduation-guard` | 3,086 | `3f44dbebfd8f43951aad4b438adc331ba5347f7bd6a7c235f065ea85d890bdb6` |
| `target-initialization-hook` | 1,438 | `51be7d04e8cf575afb0a26e029edd6059705ef9df24ac40c77c84c95515dc178` |
| `target-launch-deployer` | 19,483 | `0eeb9abfd979356ab80411eb9bec108c8cfff89879a8495b2fc58cb490ee45a2` |
| `target-launch-forwarder` | 3,574 | `d30325110a0ddc34d427ec5b598831165a04ef9ebea2edf41d08ea29db6b5146` |

The target token's full rebuilt creation payload is 8,058 bytes with SHA-256 `026c3bab7fa6a9fb3402af9874870114e9731fddee906289e08371e9cf9be577`, identical to the user-provided payload.

## Separate current-website runtime results

| Contract | Runtime bytes | SHA-256, identical capture and rebuild |
| --- | ---: | --- |
| `factory` | 23,095 | `c3c622e4673f8f1598a3bc69b11e87d4188d0f9480bb86dedb792bf42fb145f8` |
| `fee-escrow` | 1,969 | `ecfda94a9a6445f932bdc2774f689c676be80a6fb4d5f490c0b07ddb54d27ac2` |
| `locker` | 2,570 | `a38c034933e21aaf7d69696b79375fd7fedbb4a305ade49564ec82eb0ab909c3` |
| `graduation-executor` | 9,195 | `a63df3265262dff053a513fef0d9da1eee5148e7d940a93e7f2f1638fce93d9e` |
| `graduation-guard` | 3,086 | `3f44dbebfd8f43951aad4b438adc331ba5347f7bd6a7c235f065ea85d890bdb6` |
| `initialization-hook` | 1,438 | `51be7d04e8cf575afb0a26e029edd6059705ef9df24ac40c77c84c95515dc178` |
| `launch-deployer` | 19,592 | `8c2f4824b81e2210b9c7ac6510b69a049f78dd4f45f57a19d7f589e9c5099d22` |

These results establish the captured runtime identity for the listed addresses, not an audit of all deployed instances, all external Uniswap contracts, the web application, or future configuration changes. Source identity and vulnerability-review coverage are separate claims.

## Local runtime tests

With Foundry 1.7.1 and a Solidity compiler available, run:

```sh
forge test --root clank/tests --use 0.8.26 -vv
```

The harness deploys the original supplied initcode and compares its result with the captured runtime. It does not rebuild the production contract with the harness compiler. The recorded local run used `--use /opt/miniconda3/bin/solc` (0.8.28); CI uses 0.8.26. Seven tests passed, including 256 fuzz cases. See [results](../evidence/target-token-tests.txt).

The historical compiler is retained for faithful reproduction, not recommended as a security baseline for a new deployment. See the [compiler advisory assessment](AUDIT.md#cl-06--historical-compiler-has-published-bug-advisories).
