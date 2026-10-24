# Local research harnesses

These experimental tests are preserved separately from the validated suites in
[`../../tests/`](../../tests/) and [`../../critical-tests/`](../../critical-tests/).
They are not part of the reported 28 passing tests or the CI acceptance suite.

| Files | Purpose | Evidence status |
| --- | --- | --- |
| `FactoryLaunchAdmin.t.sol` | Factory authorization, router refunds and recovery using mocked dependencies | Not validated for this publication |
| `curve/CurveAudit.t.sol` | Curve accounting, round trips, exits and callbacks | A saved fuzz failure needs investigation |
| `curve/ExtremeParams.t.sol` | Boundary parameter experiments | Includes diagnostic probes; a passing probe alone does not establish correctness |
| `graduation/GraduationAudit.t.sol` | Local graduation, locker and escrow integration | Uses supplied binary fixtures whose build provenance has not been independently verified |

The saved input in [`observations/all-holders-exit-counterexample.json`](observations/all-holders-exit-counterexample.json)
and test name in [`observations/last-failing-test.txt`](observations/last-failing-test.txt)
were recovered from the local Foundry cache. They are observations, not a confirmed
contract vulnerability or evidence of live exploitation. The input must be replayed
against the applicable source and the failed assertion diagnosed before drawing a
security conclusion. No test result was discarded to make a suite appear passing.

With Foundry and Solidity 0.8.26 installed, run from the repository root:

```sh
forge test --root clank/research/local-harnesses --use 0.8.26 -vv
forge test --root clank/research/local-harnesses/curve --use 0.8.26 -vv
```

The configuration uses local recovered sources and runs offline. The compiler must
already be installed. Generated output and cache directories are ignored. These
harnesses use a local EVM; they do not broadcast transactions.
