# Published recovery and verification record

2026-10-24 — Published public repository:
[**lalalune/daosfun-source**](https://github.com/lalalune/daosfun-source).

The verified source revision is
[`9b654c4e94cbb92ac88ac6268431ab780964161c`](https://github.com/lalalune/daosfun-source/commit/9b654c4e94cbb92ac88ac6268431ab780964161c).
The follow-up commit adds documentation, notices, provenance, repository metadata,
and a stronger verification helper that checks all 70 source/configuration files.
The compiled Rust source, Cargo configuration and build scripts remain unchanged
from the tested revision. The successful runs below tested that revision; this
record does not claim a separate hosted run against the follow-up commit.

## Delivered

- [Recovered Anchor/Rust source](../programs/) and [pinned dependencies](../Cargo.lock).
- [Original captured binary](../evidence/mainnet.so), [rebuilt ELF](../binaries/dao_v1.so),
  and [rebuilt account-padded binary](../binaries/dao_v1.deployed.so).
- [Portable build instructions](BUILD.md), [fixture provenance](../evidence/README.md),
  and [verification evidence](../repro/).
- [First-pass findings](../audit/FIRST_PASS.md), [second-pass findings](../audit/SECOND_PASS.md),
  [review scope](SECURITY_SCOPE.md), and [prior patch review](../audit/PRIOR_PATCH_REVIEW.md).

## Hosted verification

| Check | Result | Evidence |
| --- | --- | --- |
| Artifact checks, differential suite and security reproductions | Passed; **410/410 differential cases** across 15 suites and **6/6 security scripts** | [GitHub Actions run](https://github.com/lalalune/daosfun-source/actions/runs/40084470193), [record](../repro/hosted-verification.json) |
| Clean source build on Ubuntu 24.04 | Passed, using a freshly downloaded official toolchain and all 264 dependency crates, with an initially absent build target | [GitHub Actions run](https://github.com/lalalune/daosfun-source/actions/runs/40084472477), [record](../repro/hosted-rebuild.json) |
| Downloaded hosted artifacts | Independently compared; both binaries match exactly and the source manifest matches the repository | [Rebuild evidence](../repro/hosted-rebuild.json) |

The full 1,120,784-byte original and rebuilt account-padded binary share SHA-256:

```text
5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d
```

The 1,041,728-byte ELF has SHA-256
`145716b96a30edc81413a77caea1c06c8aaf6adf3ad65b1576d6b9469f226e07`.
The remaining 79,056 bytes are generated zero allocation padding. The build uses
explicit recovered linker ordering; byte equality does not uniquely establish the
original author's source identifiers, comments or historical build configuration.

## Security outcome

The first pass contains five confirmed findings: one critical and four medium.
The second pass confirms **TR-5, low severity**: a zero-credit caller can fix a
redemption snapshot before later deposits and strand those later funds. This
formalizes an earlier snapshot observation with signed local reproduction and a
control. The SOL rent-remainder failure hypothesis was **not reproduced** in the
tested VM and is not counted as a vulnerability. The earlier patch's nested-CPI
filtering gap remains a source-level concern, not a runtime-confirmed new finding.

The faithful source deliberately preserves these behaviors. **No fix has been
deployed**, and passing security reproductions means the documented behaviors
were observed—not that the source is secure. This review is not exhaustive.
Additional findings can be submitted through the enabled
[private vulnerability-reporting form](https://github.com/lalalune/daosfun-source/security/advisories/new).
