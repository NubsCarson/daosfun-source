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

The original research files are in a compressed [evidence bundle](daosfun-lab-evidence.tar.zst).
[`MANIFEST.json`](MANIFEST.json) lists each bundled path, byte length, and
SHA-256, as well as the upstream lab commit. The bundle retains the complete
daos.fun analysis, virtual-XYK analysis, five current-program disassemblies,
current and reconstructed program binary captures, read-only RPC receipts,
local test scripts, and two narrow native Rust behavior models for PumpXYK
`migrate_v2` and FeeShare payouts. The models are not original on-chain source
or SBF rebuilds. The bundle excludes
Meteora DLMM/HumidiFi research except where those external programs are
explicit CPI dependencies of a daos.fun test.

The refreshed bundle pins private lab commit
`ed2357f44d9a25ea1f12783164c0c62d7f4f744b`, contains **991** scoped
files (116,608,715 uncompressed bytes), and has archive SHA-256
`d3e2b07d39f06935baee60acd7b25ead430280126361670c3d6ab0126a1b1a11`.
All **26** directly linked JSON receipts match bundled member size and
SHA-256. The daos.fun offline gate passed **111** commands; strict full
behavior remains **0/52**.

The most reviewable distinct results are summarized in the adjacent notes.
A small selection of key JSON receipts is also available directly in
[`receipts/`](receipts/), without unpacking the full bundle:

- [`DAO_V1.md`](DAO_V1.md): source-era replays, DAO/DBC migration, issuance,
  delegation and redemption paths, and independent checks of the published
  BM-1 finding.
- [`FOUNDER.md`](FOUNDER.md): exact tested presale-goal model, allocation and
  vesting controls.
- [`FEE_SHARE.md`](FEE_SHARE.md): `Option<Pubkey>` decoding, fee conservation,
  signed payout and legacy fee-authority CPI, plus a bounded native Rust
  payout model with 96/96 local differential matches.
- [`PUMP_XYK.md`](PUMP_XYK.md): source-era migration transfer formula and
  failure rollback, plus a distinct current `migrate_v2` native Rust data
  model with 72 full-data matches and eight parser-rejection matches.
- [`VIRTUAL_XYK_AND_TR2_TR3.md`](VIRTUAL_XYK_AND_TR2_TR3.md): swap/liquidity
  and fee-authority controls, current Curve census, and bounded exposure
  checks for the DAO cosigner and redemption findings.

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
