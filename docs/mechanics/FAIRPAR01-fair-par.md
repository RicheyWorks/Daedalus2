# FAIRPAR01 - Fair Par Calibrator (G600, Prismheart balance lane)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/FairPar.java` (rules authority)
C++: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshFairParCore.h` (namespace `daedalus::marsh`)
Tests: `FairParTest` (5 tests), `MarshCoresParityTest.fairParMatchesCpp`, `marsh_fair_par_core_test.cpp` (27 checks,
g++ and clang++ with ASan+UBSan in `marsh-cores.yml`). Source only; no Unreal, no new assets.

## Story / Daedalus hook

Every Prismheart cabinet shows a bronze, silver and gold par. Hand-picked pars feel unfair: too easy on one cabinet,
impossible on the next. The census-board heron sets them instead: before a cabinet opens, a seeded casual bot plays
it a few hundred times, and the pars come from what the bot actually scored.

- `FairPar.translocation(plan, runs, seed)` plays TRANS01 (G589); `FairPar.reedRelease(rr, runs, seed)` plays
  REEDREL01 (G593). Both return `Pars` with `tier(score)` for the player's result.
- The cabinet shows the player's tier after a run: NONE, BRONZE, SILVER, GOLD, or PERFECT (the exact optimum).
- `separated()` is the designers' warning light: false means two tiers need the same score.

## Rules

1. Score = survival chance = 1 - crash risk of the player's plan (higher is better), on the cabinet's own seeded
   shocks (common random numbers), so the bot and the player face the same weather.
2. The casual bot picks a random release count each year (at most the yearly cap and what is left), then sends any
   leftover birds as early as the cap allows. It always spends the whole budget. On REEDREL01 it also picks a random
   reedbed option.
3. Sort the bot scores. A tier with share p (bronze 60 %, silver 25 %, gold 5 %) gets the score at index
   n - ceil(p n), computed in integers: at least that share of bot runs reaches it.
4. Pars are capped at the exact optimum (`best()`), which is the PERFECT tier.
5. Hits = the share of bot runs at or above each par; ties can push them above the target share.
6. Bot hashes: SplitMix64 finalizer of (seed, run, pick, salt), stateless, mirrored in C++. Not a new generator.

## Default cabinets (first balance findings)

| Cabinet | Bot runs | Bronze | Silver | Gold | Perfect | Hits (B/S/G) | Separated |
|---|---|---|---|---|---|---|---|
| TRANS01 default (seed 7) | 200 | 0.7875 | 0.7875 | 0.7925 | 0.7975 | 0.61 / 0.61 / 0.065 | no |
| REEDREL01 default (seed 23) | 120 | 0.0067 | 0.900 | 1.000 | 1.000 | 0.82 / 0.29 / 0.14 | no |

- **TRANS01 is flat.** Any plan that spends all 10 birds lands within one percentage point of the best plan, so bronze
  and silver need the same score. A tuning pass should make the timing matter more, for example a tighter yearly cap,
  a smaller budget or more noise.
- **REEDREL01 is all-or-nothing.** The reedbed choice decides almost everything (median bot survival 0.07, top bots
  1.0), and 14 % of bot runs already hit the optimum. A tuning pass should narrow the gap between reedbed options or
  make the schedule matter.

## Parity

`MarshCoresParityTest.fairPar()` writes `engines/unreal/core-test/marsh_fair_par_parity.txt` with
`-Dmarsh.parity.write=true`: 5 fixed score lists (exact), 6 bot schedules and hashes (exact), 3 TRANS01 and 2 REEDREL01
cabinets. Cabinet pars match within one cabinet run and hit shares within two bot runs, because a libm last-ulp
difference could move one borderline run.
