# Supplemental daos.fun binary research

This contribution packages an independent, offline research lab for the five
Solana programs identified by the daos.fun client IDLs. It complements the
reconstructed `dao_v1` source in this repository. It does not change program
source, claim a deployed fix, or include the unrelated Clank project.

The lab first captured finalized ProgramData binaries and the site IDLs, then
mapped all **52 declared selectors** to current-binary dispatcher wrappers.
Across the five programs, **52/52** selectors have a bounded local success
with the exact current **target-program ELF** loaded. A downstream CPI
dependency may be from an older deployment: selected `dao_v1.init_curve`
and `dao_v1.migrate_bonding_to_meteora` paths succeed with the current DAO
ELF and source-era CP DAMM, while their tested current-CP controls fail
6067. A separate per-handler audit finds **50/52 selected bounded paths**
load current target and custom CPI executables: DAO **16/18**,
FeeShare **9/9**, Founder **6/6**, Pump **9/9**, and VirtualXYK **10/10**.
System, SPL Token and ATA execution uses the local runtime; restored or
synthetic account states are not a live mainnet prestate. These counts are an
entrypoint inventory, **not** full behavior coverage: untested
authority, token, account-state, arithmetic, upgrade, and historical branches
remain. `dao_v1` is the one program whose current binary also matches the
byte-identical reconstruction in this repository.

| Program | Current target ELF bounded success | Selected current custom stack | Strict full behavior | Current captured SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `dao_v1` | 18/18 | 16/18 | 0/18 | `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d` |
| FeeShareTraderDAO | 9/9 | 9/9 | 0/9 | `88df1b4ddb152d4159b41b9eba68ab74e6f0e14c1930bad5828c44a14a3ca4f8` |
| FounderDAO | 6/6 | 6/6 | 0/6 | `816bc6d42ffea7d63bd7b1287589413aef04d8f7dceb34dd274a0f7872d40aa2` |
| PumpXYK | 9/9 | 9/9 | 0/9 | `2238aa5b96fc29e7693174b20d75063df2e1dfba28c26c5346338c23732e2fb9` |
| VirtualXYK | 10/10 | 10/10 | 0/10 | `c151c6b15b84d8bfc47a5f2e0e5b9e04babff0263a1125a9e8dcb07df6144377` |

The [DAO binary provenance](receipts/dao-v1-binary-provenance.json) and
[other-program version audit](receipts/non-dao-current-elf-version-audit.json)
pin the root handler ELF hash behind each bounded-success count. CPI
dependency versions are pinned in the
[DAO current-stack audit](receipts/dao-v1-custom-stack-version-audit.json)
and other-program audit; the
[virtual custom-stack audit](receipts/custom-stack-version-audit.json)
checks its ten selected direct paths.

Four [FeeShare](receipts/daos-fee-share-baseline.json),
[Founder](receipts/daos-founder-baseline.json),
[Pump](receipts/daos-pump-baseline.json), and
[VirtualXYK](receipts/daos-virtual-baseline.json) ELF baselines pin each
current file's section hashes, ELF extent, and zero-filled allocation
padding. They explicitly record **no source-built candidate** for those
programs at their capture checkpoint. Later
[incomplete full-interface candidates](receipts/daos-full-candidate-status.json)
expose the current selector surfaces but retain missing or failing handler
bodies. Neither those SBF candidates nor the native Rust behavior slices
match a deployed whole-program binary. The
[exact-build feasibility checkpoint](DAOS_EXACT_BUILD_FEASIBILITY.md) compares
all four current ELF layouts with Shaw's `dao_v1` recipe and identifies
FeeShare as the smallest next whole-program candidate, while recording that
none of the four has a source-built byte match. The
[FeeShare v1.41 compiler-format probe](receipts/daos-fee-share-v141-toolchain-probe.json)
is a toolchain hypothesis, not an exact FeeShare rebuild.

The original research files are in a compressed [evidence bundle](daosfun-lab-evidence.tar.zst).
[`MANIFEST.json`](MANIFEST.json) lists each bundled path, byte length, and
SHA-256, as well as the upstream lab commit. The bundle retains the complete
daos.fun analysis, virtual-XYK analysis, five current-program disassemblies,
current and reconstructed program binary captures, read-only RPC receipts,
local test scripts, and four narrow native Rust behavior models for PumpXYK
`migrate_v2`, FeeShare payouts and post-CP-claim accounting, and Founder
presale pricing. The models are
not original on-chain source or SBF rebuilds. Four separate incomplete
Anchor/SBF interface candidates and their non-secret status receipts are
also included; **they are not matching or deployable replacements**. The
bundle excludes
Meteora DLMM/HumidiFi research except where those external programs are
explicit CPI dependencies of a daos.fun test.

The refreshed bundle pins private lab commit
`a24e968bf5242726fdbc10d6fa6ebc3d7d78e8fe`, contains **1,110** scoped
files (118,681,383 uncompressed bytes), and has archive SHA-256
`4168dfcb1a12da95494b33056e1b51cea430b8f919322e49c1ea68dc997e57b7`.
All **54** direct JSON receipts match bundled member size and
SHA-256. The daos.fun offline gate passed **112** commands; strict full
behavior remains **0/52**.

The most reviewable distinct results are summarized in the adjacent notes.
A small selection of key JSON receipts is also available directly in
[`receipts/`](receipts/), without unpacking the full bundle:

- [`DAO_V1.md`](DAO_V1.md): source-era replays, DAO/DBC migration, issuance,
  delegation and redemption paths, and signed offline checks of BM-1,
  TR-1 expiry, TR-5 redemption timing, and six current-CP variants.
- [`FOUNDER.md`](FOUNDER.md): tested presale-goal model, allocation and vesting
  controls, a native Rust goal/amount slice with 120/120 local differential
  matches, and a fresh signed Founder-to-Pump lifecycle.
- [`FEE_SHARE.md`](FEE_SHARE.md): `Option<Pubkey>` decoding, fee conservation,
  signed offline Surfpool external-fee claim, payout and counter reachability
  checks, legacy fee-authority CPI, and a bounded native Rust payout model
  with 96/96 creator cases plus 49/49 referrer/error-order matches, and a
  separate 15-case post-CP-claim accounting slice.
- [`PUMP_XYK.md`](PUMP_XYK.md): source-era migration transfer formula and
  failure rollback, current `migrate_v2` native Rust data model with 72
  full-data matches and eight parser-rejection matches, and signed trade
  lifecycles on restored and fresh Curves.
- [`VIRTUAL_XYK_AND_TR2_TR3.md`](VIRTUAL_XYK_AND_TR2_TR3.md): swap/liquidity
  and fee-authority controls, current Curve census, conditional synthetic
  Token-2022 transfer-fee and LP-exit checks, and bounded exposure checks
  for the DAO cosigner and redemption findings.

Constructed test transactions execute in LiteSVM or offline Surfpool; one
saved historical transaction was also resimulated with public RPC's
read-only `simulateTransaction`. Other public RPC calls read accounts,
binaries, and historical transactions. No real user-wallet signature,
fund transfer, or submitted mainnet transaction is part of this
contribution. An error from one account mutation rules out only that tested
state. The captured programs remain upgradeable; binary hashes and account
slots are part of every result's scope.

To check every bundled member without extracting it (with `zstd` installed), run:

```sh
python3 research/independent-lab/verify_bundle.py --require-external research/independent-lab/daosfun-lab-evidence.tar.zst
```

Replaying the full lab
requires Python dependencies, external CPI binaries, and snapshots documented
in the bundle. This contribution does not extend the byte-identical source
claim from `dao_v1` to the other four programs.
