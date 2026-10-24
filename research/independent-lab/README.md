# Supplemental daos.fun binary research

This contribution packages an independent, offline research lab for the five
Solana programs identified by the daos.fun client IDLs. It complements the
reconstructed `dao_v1` source in this repository. It does not change program
source, claim a deployed fix, or include the unrelated Clank project.

The lab first captured finalized ProgramData binaries and the site IDLs, then
mapped all **52 declared selectors** to current-binary dispatcher wrappers.
Across the five programs, **52/52** selectors have a bounded local success
with the exact current **target-program ELF** loaded. A downstream CPI
dependency may be from an older deployment: DAO `init_curve`, for example,
succeeds with the current DAO ELF and source-era CP DAMM, while the tested
current DAO + current CP DAMM combination fails 6067. The full
current-dependency-stack denominator is still being audited. These counts are an
entrypoint inventory, **not** full behavior coverage: untested
authority, token, account-state, arithmetic, upgrade, and historical branches
remain. `dao_v1` is the one program whose current binary also matches the
byte-identical reconstruction in this repository.

| Program | Exact-current target ELF bounded success | Strict full behavior | Current captured SHA-256 |
| --- | ---: | ---: | --- |
| `dao_v1` | 18/18 | 0/18 | `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d` |
| FeeShareTraderDAO | 9/9 | 0/9 | `88df1b4ddb152d4159b41b9eba68ab74e6f0e14c1930bad5828c44a14a3ca4f8` |
| FounderDAO | 6/6 | 0/6 | `816bc6d42ffea7d63bd7b1287589413aef04d8f7dceb34dd274a0f7872d40aa2` |
| PumpXYK | 9/9 | 0/9 | `2238aa5b96fc29e7693174b20d75063df2e1dfba28c26c5346338c23732e2fb9` |
| VirtualXYK | 10/10 | 0/10 | `c151c6b15b84d8bfc47a5f2e0e5b9e04babff0263a1125a9e8dcb07df6144377` |

The [DAO binary provenance](receipts/dao-v1-binary-provenance.json) and
[other-program version audit](receipts/non-dao-current-elf-version-audit.json)
pin the root handler ELF hash behind each bounded-success count. CPI
dependency versions are recorded separately where known.

The original research files are in a compressed [evidence bundle](daosfun-lab-evidence.tar.zst).
[`MANIFEST.json`](MANIFEST.json) lists each bundled path, byte length, and
SHA-256, as well as the upstream lab commit. The bundle retains the complete
daos.fun analysis, virtual-XYK analysis, five current-program disassemblies,
current and reconstructed program binary captures, read-only RPC receipts,
and local test scripts. It excludes
Meteora DLMM/HumidiFi research except where those external programs are
explicit CPI dependencies of a daos.fun test. The most reviewable distinct
results are summarized in the adjacent notes. A small selection of key JSON
receipts is also available directly in [`receipts/`](receipts/), without
unpacking the full bundle:

- [`DAO_V1.md`](DAO_V1.md): source-era replays, DAO/DBC migration, issuance,
  delegation and redemption paths, and independent checks of the published
  BM-1 finding.
- [`FOUNDER.md`](FOUNDER.md): exact tested presale-goal model, allocation and
  vesting controls.
- [`FEE_SHARE.md`](FEE_SHARE.md): `Option<Pubkey>` decoding, fee conservation,
  and legacy fee-authority CPI.
- [`PUMP_XYK.md`](PUMP_XYK.md): source-era migration transfer formula and
  failure rollback.
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
