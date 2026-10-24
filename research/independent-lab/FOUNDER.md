# FounderDAO: bounded allocation and presale recovery

The pinned current FounderDAO ProgramData is `Daosz93P15uZ1aTFTrBUAJyU1KERmZm3XQ5u4hbfHVQS`, SHA-256
`816bc6d42ffea7d63bd7b1287589413aef04d8f7dceb34dd274a0f7872d40aa2`
(last deployment slot 328988984). All six site-IDL handlers have a bounded
local success, and historical successful transactions were located for all
six. None is certified as fully reversed. Paths below name files inside the
[evidence bundle](daosfun-lab-evidence.tar.zst).

The `init` boundary matrix accepts exactly 1, 2, 3, and 4 quadrillion raw
token units of team allocation among 21 tested values on each of two source
instruction templates. It reserves 1 quadrillion for DAO allocation and
sets curve allocation to `9e15 − team_allocation`. The program disassembly
contains equality checks for those four cases. In 1,154 isolated tests over
40 valuation/allocation rays, `funding_goal = valuation × (9 − team/1e15)`
fails with 6010 and **one unit above** is the first success. These tests do
not close high-valuation overflow or alternate account states.

For `start_presale`, the source-era Founder binary constructs a Fundraise
CPI with a seven-day duration, the caller's token deposit, and a calculated
funding goal. Two captured historical CPI arguments agree with the local
replays; Fundraise receives an already computed goal. Presale amounts from
zero through `4e15` succeed in tested cases; `4e15 + 1` fails 6007. The
source-era disassembly and temporary local slope instrumentation support the
following **bounded integer model**. Write `T = 10^15`, `C` for curve
allocation, `V` for initial valuation, `G` for initial funding goal, and `A`
for presale amount:

```text
m = floor(10*C/11)
S = nearest_integer(20*(G*T - V*m)*T/m^2)
goal = ceil((20*V*A*T + S*A^2)/(20*T^2))
```

This model matches **1,119/1,119** unmodified local goal outputs, including
200 held-out wide cases and variants designed to distinguish the floor point
from an idealized rational point. A temporary, explicitly modified ELF is
used only to identify and vary the intermediate slope; final goal comparisons
run on the original pinned binary. Decimal overflow, exact half-way
rounding outside the tested domain, and other error branches remain open.

`claim_team_allo` moves `3e15` raw DAO-token units to a vest schedule ATA
and flips a one-time flag in a restored local prestate. An underfunded vault
fails and all five watched protocol accounts roll back. Four `start_vest`
transactions succeed locally after clearing an already-set start tag in
their captured later accounts; this is a hypothetical prestate. A synthetic
143-byte legacy `migrate_v2` account grows to 155 bytes and maps the old
allocation fields as observed, but exact historical input bytes are absent.

A separate 56-case `start_vest` authority matrix uses real local signatures
on four restored schedules. A distinct correctly signed payer succeeds in
all four, while unsigned payer, already-started schedule, empty Curve,
wrong account owner and wrong Vest program controls reject. Resetting only
the Vest start tag is synthetic, so these cases show a bounded permissionless
trigger, not a reachable premature start or fund-loss claim. See the
[signed authority matrix](receipts/founder-start-vest-authority-matrix.json).

Key receipts: `analysis/daos_fun/founder-init-allocation-boundaries.json`,
`founder-init-goal-thresholds.json`, `founder-presale-cpi-source-attribution.json`,
the [static trace](receipts/founder-presale-static-trace.json),
`founder-presale-slope-patch-probes.json`,
`founder-start-presale-branch-matrix.json`,
`founder-claim-team-branch-matrix.json`, and
`founder-start-vest-branch-probes.json`. The overall replay gate is
`analysis/daos_fun/offline-verification.json`.
