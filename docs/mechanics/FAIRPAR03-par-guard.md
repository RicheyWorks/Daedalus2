# FAIRPAR03 - Fair Par regression guard (G607; Prismheart balance lane)

Guard file: `engines/unreal/core-test/fair_par_guard.txt` (hand-kept; no tool writes it)
Checks:
- `python tools/minigames/fair_par.py --guard` (desktop-games.yml) re-runs the seeded Prismheart sims and fails on
  any moved par, one `PAR GUARD:` line per par.
- `prism_fair_par_core_test.cpp <fixture> fair_par_guard.txt` (engines.yml, g++ ASan+UBSan and clang++) checks
  the live C++ table, and Shardring's fixture rows, against the guard.
- `FairParTest.parGuardHolds` (Java build) checks `FairPar.marshTable()` for the six marsh cabinets, exact doubles.

## Why a separate file

`fair_par.py --write` and `-Dmarsh.parity.write` regenerate the parity fixtures from the current rules, so a rule
change plus a regen used to move a par silently. The guard holds only the bronze/silver/gold pars (39 rows:
6 marsh, 33 Prismheart). It is never regenerated, so a moved par fails CI until someone edits the guard row by
hand, which shows up as a reviewable diff.

## When a check fails

1. If the par move was not intended, fix the rule change.
2. If it was intended (a rebalance), edit the matching row in `fair_par_guard.txt` in the same PR. Regenerate the
   parity fixture as usual, and name the moved pars and the reason in the PR body. Satchel tiers, Almanac daily
   pars and trophies read these pars, so tell their owners (prism-shard-dev, 2hot2trot).

Changes that do not move a par (hit rates, medians, demo stats) only need the usual fixture regen.
