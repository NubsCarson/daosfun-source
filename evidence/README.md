# Captured programs and local test fixtures

This directory contains the captured DAO executable, external program fixtures,
and public account samples used by the local comparison and security tests.
The fixtures are versioned evidence, not a live view of mainnet.

Every binary and account JSON fixture is listed with its size and SHA-256 in
[`repro/evidence-manifest.json`](../repro/evidence-manifest.json). Test results are
stored separately under `audit/results/` or the selected local test output directory.

## Program binaries

| File | Origin and purpose |
| --- | --- |
| `mainnet.so` | Original captured executable for `4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM`. This is the reference for byte identity and original-program security behavior. |
| `token-2022.so` | Captured external Token-2022 program used in local token and account tests. |
| `fundraise.so` | Captured external fundraise program used to exercise the DAO's CPI integration. |
| `hedgefun.so` | Captured external hedgefun program used for legacy curve and migration integration. |
| `meteora-dbc.so` | Captured external Meteora Dynamic Bonding Curve program used for DBC integration and the cross-pool finalization reproduction. |
| `meteora-damm-v2.so` | Captured external Meteora DAMM v2 program used to test compatibility with the recovered DAO's calls. |
| `meteora-damm-v2-0.1.3.so` | **Locally built compatibility fixture**, from DAMM source revision `e9ffd023db1974d7a91c24e3b1c58916397bf5ae`. This is not claimed to be a historical deployed DAMM binary. |

The DAO capture is 1,120,784 bytes, including its trailing allocation padding, with
SHA-256 `5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d`.
The separately rebuilt comparison artifacts are in [`binaries/`](../binaries/).

The captured DAMM program rejects the recovered DAO's older fee-parameter encoding
with error 6067 (`InvalidCompoundingFeeBps`) in the relevant compatibility tests.
The locally compiled DAMM fixture lets selected tests exercise later migration and
initialization steps beyond that rejection. Results obtained with that fixture
must not be described as a successful integration against the captured DAMM
executable or as proof of historical deployment behavior.

Recorded upstream source references are in
[`repro/dependency-source-provenance.json`](../repro/dependency-source-provenance.json).
A source revision identifies a source checkout. By itself, it does not prove that
a captured on-chain binary was built from that revision or identify its original
compiler and build settings.

## Account JSON

The JSON files are public account/configuration samples used as inputs for local
fixtures. Tests may load those samples and replace balances, authorities, flags,
or other fields in a local VM to isolate a particular check. Such modified states
are synthetic test conditions, not claims about the sampled accounts' current
mainnet state. Deterministic test keypairs are local fixtures; no real user's
private key is included or required.

Local transaction success, byte identity, and live integration compatibility are
separate forms of evidence. See the [security scope](../docs/SECURITY_SCOPE.md) and
the individual test reports for their assumptions.

## Meteora upstream notices

The recorded Meteora source references point to
[Meteora DAMM v2](https://github.com/MeteoraAg/damm-v2) and
[Meteora Dynamic Bonding Curve](https://github.com/MeteoraAg/dynamic-bonding-curve).
Copies of the corresponding upstream terms are preserved in
[`third_party/METEORA_DAMM_LICENSE.md`](../third_party/METEORA_DAMM_LICENSE.md) and
[`third_party/METEORA_DBC_LICENSE.md`](../third_party/METEORA_DBC_LICENSE.md).
Their required notices are reproduced here verbatim:

> Required Notice: All underlying software code is subject to the licence set out at https://github.com/MeteoraAg/damm-v2.

> Required Notice: All underlying software code is subject to the licence set out at https://github.com/MeteoraAg/dynamic-bonding-curve

These are upstream notices for the referenced components. This document does not
assign a repository-wide license or replace the upstream terms.
