# Clank / AGI source recovery

**The selected contract is a different program from the Solana DAO.** `0xfa31d04462746aaa24bc7e5626403e09e4b106ec` is the **AGI ERC-20 token on Robinhood Chain**, chain ID **4663**. Its recovered historical Solidity source reproduces the supplied creation code and deployed runtime byte for byte.

The target token belongs to an **older Clank factory**, not the factory currently advertised by `clank.trade/v1/config`:

| Role | Address |
| --- | --- |
| Selected AGI token | `0xfa31d04462746aaa24bc7e5626403e09e4b106ec` |
| AGI's historical factory | `0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1` |
| AGI's bonding curve | `0xa042794f670cfe57209438cbe63dbdf4424b6dff` |
| Current website factory | `0x798daAa0707C1e538bB5Acf0867Ac0e1A84cccF2` |
| Original, unrelated Solana program | `4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM` |

At block **96,692,586** (2026-10-24 10:22:08 UTC), AGI's curve is already graduated (`PoolCreated`). Its position NFT **3,034,864** is recorded in and owned by its permanent locker. AGI has a fixed supply of **1,000,000,000 tokens**, 18 decimals, and intentionally rejects all burning. The newer factory's token implementation allows burning; its source must not be substituted for AGI's.

## Original and rebuilt bytes

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Supplied creation payload](evidence/contracts/target-token.user-creation.bin) | 8,058 | `026c3bab7fa6a9fb3402af9874870114e9731fddee906289e08371e9cf9be577` |
| [Rebuilt creation payload](binaries/target-token.creation.bin) | 8,058 | `026c3bab7fa6a9fb3402af9874870114e9731fddee906289e08371e9cf9be577` |
| [RPC-captured runtime](evidence/contracts/target-token.runtime.bin) | 3,139 | `190f2abee01041531efc2c2618d8f7f1b1ae8ba9bb183e42f786982b4e4bf155` |
| [Rebuilt runtime](binaries/target-token.runtime.bin) | 3,139 | `190f2abee01041531efc2c2618d8f7f1b1ae8ba9bb183e42f786982b4e4bf155` |

The [supplied runtime](evidence/contracts/target-token.user-runtime.bin) also matches the independent RPC capture. The creation payload consists of **7,066 bytes compiled from source plus 992 bytes of original ABI constructor arguments**. Constructor arguments are inputs, not recovered source code. Deployment-specific immutable addresses are derived from those arguments. No executable instruction or metadata bytes are copied into the compiled output to force a match. A local EVM execution of the supplied creation payload independently produces the exact runtime. The full payload also derives the exact target address under CREATE2 using the historical launch-deployer and on-chain launch ID ([proof](evidence/contracts/target-create2.json)).

## Read and reproduce

- [Exact historical token source](verified/target-factory/sources/contracts/ClankLauncherToken.sol)
- [Historical factory and related sources](verified/target-factory/sources/contracts/)
- [Consolidated security review](docs/AUDIT.md)
- [Compiler, dependency and reproduction details](docs/BUILD.md)
- [Target token comparison proof](evidence/build/target-token.json)
- [Target state](evidence/contracts/target-state.json), [liquidity ownership and governance evidence](evidence/contracts/target-context.json)
- [Local runtime tests](tests/TargetToken.t.sol) and [results](evidence/target-token-tests.txt)

Sources were recovered from the historical factory's public [Sourcify record](https://sourcify.dev/server/v2/contract/4663/0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1?fields=all), then compiled and compared. The direct token Sourcify lookup was unavailable; the successful bytecode match establishes that the historical factory's token source is the right implementation. The [explorer token page](https://robinhoodchain.blockscout.com/token/0xfa31d04462746aaa24bc7e5626403e09e4b106ec?tab=contract_code) identifies the user's target.

```sh
python3 clank/scripts/rebuild_target.py
```

The build uses the exact official Solidity **0.8.26+commit.8a97fa7a** compiler, original source-unit paths, optimizer/IR/EVM settings, and archived dependency source contents. This is an EVM/Solidity project; Anchor is used only for the unrelated Solana reconstruction at the repository root.

The security review confirms no critical or high exploit in the selected token. It records an intentional burn-interface limitation and conditional surrounding-protocol risks with explicit applicability limits. Seventeen local security tests pass, including 4,096 fuzz cases. No deployment, remediation, live trading, or on-chain exploit was performed.

## Evidence scope

Public reads are pinned to block hash `0xd2254f48f5922f7ff13223026dabe708729ed9e187eaf852e3a1343303201c10`. The web configuration is a separate contemporaneous capture, not historical chain state. All runtime matches refer to this captured block; future configuration changes are outside the snapshot.

`verified/` preserves contract-specific source inputs, including third-party SPDX notices. Repeated paths across those directories are intentional: different verification units and historical versions can have different contents. `evidence/contracts/` contains public RPC/source records and raw original bytecode; `binaries/` contains reconstructed comparison outputs. Downloaded compiler and intermediate build caches are ignored.
