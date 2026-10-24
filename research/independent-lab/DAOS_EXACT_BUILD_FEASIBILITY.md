# daos.fun exact Rust/SBF build checkpoint

This is a reviewer-facing copy of the exact report bundled at
`analysis/source_reconstruction/daos-exact-build-feasibility.md`; relative
links are adjusted for this repository layout.

Shaw's [`dao_v1` reconstruction](../../README.md)
rebuilds its captured binary byte for byte. The four other current daos.fun
programs have pinned [ELF/section baselines](README.md) and bounded native
Rust behavior models, but **no full source-built candidate or byte-identical
build**. A matching native behavioral model is not a matching SBF executable.

| Current program | ELF bytes | `.text` bytes | Relocations | Allocation padding | Whole-program source candidate |
| --- | ---: | ---: | ---: | ---: | --- |
| [`dao_v1`](../../repro/final-proof.json) | 1,041,728 | 951,456 | 3,550 | 79,056 | [Shaw's byte-identical rebuild](../../docs/BUILD.md) |
| [FeeShareTraderDAO](receipts/daos-fee-share-baseline.json) | 522,216 | 468,912 | 1,904 | 0 | None |
| [FounderDAO](receipts/daos-founder-baseline.json) | 573,384 | 506,152 | 2,402 | 976 | None |
| [PumpXYK](receipts/daos-pump-baseline.json) | 684,168 | 612,376 | 2,713 | 136 | None |
| [VirtualXYK](receipts/daos-virtual-baseline.json) | 528,384 | 469,792 | 2,138 | 117,416 | None |

The five captures have standard `EM_BPF` section ordering and identical
`.shstrtab` contents. That is evidence of a similar linker family; it does
not establish matching compiler versions or source. Their deployment slots,
full ProgramData hashes and upgrade authority are pinned in
[`daos-chain-manifest.json`](receipts/daos-chain-manifest.json).

FeeShare is the smallest next whole-program build target. Shaw's
[`fee_share_trader_dao` supporting crate](../../programs/fee_share_trader_dao/src/lib.rs)
implements `initialize`, `init_with_legacy`, and `change_creator` for DAO
integration. It defaults to `no-entrypoint`, lacks six of the nine deployed
handlers, including `redeem` and fee claims, and has different source file
paths from the nine `src/instructions/*.rs` locations embedded in the
deployed FeeShare ELF. It is not a deployable FeeShare source reconstruction.
Our [FeeShare payout Rust slice](FEE_SHARE.md)
models only two accounting branches and omits Anchor account validation and
SPL Token CPI failures. The [Founder](FOUNDER.md)
and [Pump](PUMP_XYK.md) slices are also
bounded behavioral models. Shaw's `hedgefun_curve` has a different program
ID from VirtualXYK; it is not VirtualXYK source.

Shaw's [DAO build recipe](../../docs/BUILD.md)
pins Linux platform-tools v1.41 (`rustc 1.75.0-dev`, LLVM 17), Anchor 0.30.1,
Solana 1.18.26, dependencies and recovered linker/constant order for that
one DAO binary. These are hypotheses for the other programs, not
proven original settings. The next FeeShare milestone is a standalone
nine-handler Anchor reconstruction with account/error/CPI paths, followed by
clean candidate builds under a pinned toolchain, section/relocation/span
comparison, linker-order recovery and final whole-file SHA comparison.
Even a byte-identical result would establish an equivalent build artifact,
not uniquely recover historical comments or variable names.
