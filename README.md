# daosfun-source

Faithful Anchor/Rust reconstruction of Solana program
`4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM`, with the captured original,
byte-identical rebuilt binary, reproduction tooling and security findings.

**This source preserves the original vulnerabilities. It is for recovery,
comparison and review, not a remediated deployment.**

See the [publication and hosted verification record](docs/DELIVERY.md) for the
verified source commit, successful clean build, test results and security summary.

## Binary comparison

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Original capture](evidence/mainnet.so) | 1,120,784 | `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d` |
| [Rebuilt binary](binaries/dao_v1.deployed.so) | 1,120,784 | `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d` |

The rebuilt binary is identical byte for byte, including 79,056 generated zero
padding bytes matching the captured account allocation. Only the complete
account-padded artifact is retained in `binaries/`. The reconstruction uses a pinned
lockfile, official platform-tools v1.41 and explicit recovered linker section
ordering. All code/data comes from source compilation; no original executable
bytes are inserted into the build. Original comments, identifiers and historical
build settings cannot be uniquely recovered from a binary.

See [build and verification instructions](docs/BUILD.md) and
[the recorded comparison proof](repro/final-proof.json).

## Repository layout

- [`programs/`](programs/): reconstructed DAO source and supporting CPI/account crates.
- [`Cargo.lock`](Cargo.lock), [`Anchor.toml`](Anchor.toml): pinned dependency and Anchor configuration.
- [`binaries/`](binaries/) and [`evidence/`](evidence/): compiled comparison artifacts and public/synthetic test fixtures.
- [`scripts/`](scripts/): reproduction, comparison and local test tooling.
- [`repro/`](repro/): linker layout and verification records.
- [`audit/`](audit/): findings, local PoCs and their results.

Do not run a formatter over span-sensitive Rust when reproducing the exact build:
panic source locations affect the emitted bytes.

## Security review

The [security audit](audit/AUDIT.md) contains **six confirmed findings: one
critical, four medium, and one low**. These cover cross-pool migration fee diversion
and state corruption, missing expiry enforcement, cosigner privilege forwarding,
external token authorities surviving closure, Token-2022 redemption incompatibility,
and zero-credit snapshot creation that can strand later deposits.

The audit also preserves negative results and limitations. The SOL rent-remainder
failure hypothesis was not reproduced and is not counted as a vulnerability. Read
the [scope notes](docs/SECURITY_SCOPE.md) and
[review of the earlier patch experiment](audit/PRIOR_PATCH_REVIEW.md); a tested
patch case is not a claim that every vulnerability has been fixed.

The packaged-repository differential suite passed **410 cases across 15 suites**
([results](repro/differential-test-summary.json)); all six security scripts passed
([results](audit/results/second-pass-rerun/summary.json)). To run the
local tests after installing `requirements.txt` in a Python virtual environment:

```sh
python scripts/security_tests.py
python scripts/test_variant.py binaries/dao_v1.deployed.so .build/differential
```

The differential output directory must be new. Tests use local LiteSVM only;
no mainnet transactions are required. See [SECURITY.md](SECURITY.md) for reporting
additional findings without posting sensitive live-exploitation details publicly.
