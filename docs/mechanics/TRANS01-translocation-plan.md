# TRANS01 - Translocation Plan (contest G251)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/TranslocationPlan.java`
Tests: `TranslocationPlanTest` (11 tests). Source only; no Unreal, no new assets.

## Story / Daedalus hook

The G163 studbook aviary can spare a few cranes a year. The marsh flock (G194) is still small, and G202 says bad
years can crash it. Pip gets a budget of aviary birds and a release calendar on the census board: when should
they go out, and which cohort?

- `TranslocationPlan.of(flock, settings, seed)` runs on the G194 `CraneCohorts` matrix with G202-style log-normal
  noise (mean-one factor `exp(sigma Z - sigma^2/2)`). A crash means the total falls below the threshold at any
  census.
- `best()` searches every schedule exactly. `greedy()` adds one bird at a time and is cheap for big budgets.
- The quest compares Pip's own calendar with `best()` and shows the risk on the board.

## Default case

12 marsh adults; 10 aviary adults over 5 years, at most 6 a year; 30-year horizon; crash below 10; sigma 0.2;
400 seeded runs with common random numbers.

| Schedule | Crash risk |
|---|---|
| no release | 0.530 |
| late [0,0,0,4,6] | 0.253 |
| front-loaded [6,4,0,0,0] | 0.215 |
| even [2,2,2,2,2] | 0.213 |
| greedy [4,3,0,2,1] | 0.210 |
| exact best [4,0,6,0,0] | 0.203 |
| exact best, chicks instead of adults | 0.403 |

Best risk by budget (0, 4, 8, 12, 16, 20 birds): 0.53, 0.36, 0.23, 0.17, 0.13, 0.10. It never rises.

The lesson: release early and release breeders. Exact best schedules among the early-heavy ones differ by about
the Monte Carlo noise (about 0.02 at 400 runs). Adults halve the risk compared with chicks, matching the G194
reproductive values.

## Tests (TranslocationPlanTest, 11)

1. Best spends the whole budget and beats even, front-loaded, late and no-release schedules.
2. Greedy is never better than exact and stays within 0.03 of it (budgets 4, 10, 16).
3. More budget never raises the best risk; 20 birds beat 0.
4. A growing flock wants birds early: the first two years get at least as many as the last two, and
   front-loaded beats late.
5. Adult releases beat chick releases (same order as G194 `bestRelease()`).
6. With sigma 0 a 40-bird flock has zero risk.
7. Seeded plans replay exactly; `risk(best schedule)` equals the reported risk.
8. Bad tuning and schedules are rejected.
9. `Settings.problem` names the first bad field, and the exception message carries it.
10. `backLoaded()` fills the last years first and loses to front-loaded.
11. `riskInterval` brackets the estimate, narrows with more runs, and is exactly 0 at the low end when nothing
    crashed.

## Assets

None. Reuses Prop_Release_Crate (G142) and Prop_Studbook_Ledger (G163). Optional UI: a release calendar strip on
the census board.

## Native C++ core (G589)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshTranslocationPlanCore.h` (namespace
`daedalus::marsh`) is a header-only C++17 port of this core, built on the G585 `DaedalusMarshCraneCohortsCore.h` flock.
It covers the shared seeded shocks, `Risk`, the exhaustive `Best`, `Greedy`, `FrontLoaded`, `Even` and
`TranslocationSettings::Valid`, using the standard library only. The Java class stays the rules authority.
`MarshCoresParityTest.translocationPlan` writes golden vectors for 6 plans (3 flocks, release cohorts, no-noise and
zero-budget cases) to `engines/unreal/core-test/marsh_translocation_plan_parity.txt`.
`marsh_translocation_plan_core_test.cpp` replays them in `.github/workflows/marsh-cores.yml`. Pattern:
[NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md).

## Improvements (G589 iterations)

Each change lands in Java first. `MarshCoresParityTest` regenerates the golden vectors, and the C++ core replays
them.

1. **Clearer validation.** `Settings.problem(...)` (C++ `Problem()`) returns the first reason a tuning cannot run,
   in a fixed order with the same strings in both languages. The constructor's exception carries it. The golden file
   has 12 settings rows, one per rule plus a valid one.
2. **Back-loaded baseline.** `backLoaded()` (C++ `BackLoaded()`) is the late-heavy schedule the quest compares
   against. It is in the golden vectors with its risk.
3. **Risk confidence.** `riskInterval(schedule)` (C++ `RiskInterval`) is the 95 % Wilson score interval of the
   Monte Carlo risk. Its ends are exact at 0 and 1 crashes. Two schedules with overlapping intervals are not
   reliably different. The golden vectors include the interval for each best plan.
