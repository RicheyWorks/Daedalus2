# Glowmoss Delve

Module: `tools/minigames/glowmoss.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_glowmoss.py`. Native core: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusGlowmossCore.h` (header-only C++17 on `DaedalusPyRandomCore.h`), byte-checked against `engines/unreal/core-test/glowmoss_parity.txt` by `glowmoss_core_test.cpp`; regenerate the fixture with `python tools/minigames/glowmoss_parity.py` (`--check` in CI).

## Play
The shaft is a seeded grid of ledges, row 0 at the top; each ledge holds 1-5 crystals, has a darkness of 0-2, and may carry glowmoss or be unstable. From the surface you dig down one row at a time onto a ledge at most one column left or right of where you stand. A dig burns `1 + darkness` light and gathers the ledge's crystals; glowmoss then refills the lamp by `refill`, never above its capacity. An unstable ledge crumbles and drops you onto the ledge straight below at no dig cost, gathering its crystals and glowmoss too (one row only; nothing below the last row). Climbing out from row r costs `(r + 2) // 2` light, so if a dig leaves less than that the lamp gutters and the delve is lost. Climb out with crystals at or above the target to win. The target is `target_pct` percent of the best possible delve (exact DP over row, column and light), so every target is reachable. All rules math is integer.

Score on a win: crystals + light left after the climb, plus `PERFECT_BONUS` (5) for a perfect delve that gathered the best possible total. A loss scores the crystals gathered (a guttered lamp) or nothing extra (climbing out short).

| difficulty | cols | rows | light | refill | moss_pct | unstable_pct | target_pct |
|---|---|---|---|---|---|---|---|
| easy | 3 | 8 | 12 | 4 | 25 | 10 | 75 |
| normal | 4 | 10 | 11 | 3 | 18 | 12 | 80 |
| hard | 5 | 12 | 10 | 3 | 12 | 15 | 86 |

## Balance
`python tools/minigames/glowmoss_sim.py` plays seeds 0-999 per difficulty with three scripted players: `demo` (the exact best delve), `greedy` (a decent player: the safe ledge with the most crystals, climb once the target is met) and `random`. The targets are tuned for the greedy player to win about 80% / 50% / 25%.

| difficulty | demo | greedy | random |
|---|---|---|---|
| easy | 100% | 87% | 36% |
| normal | 100% | 49% | 6% |
| hard | 100% | 24% | 2% |

Before tuning (first release, no unstable ledges): greedy 93% / 46% / 15%, random 59% / 9% / 1%.

## Tutorial and screen
`python -m tools.minigames.glowmoss --tutorial` prints the step-by-step how-to (`TUTORIAL`); in `--play`, type `help` for it and `hint` for the best next move (a hint never changes the game). The screen shows the seed code, a lamp gauge, the climb-out cost, a legend, and `v` on the ledges you can dig next:

```
lamp [#########...] 9/11  climb-out cost 1  crystals 2/22
legend: @ you  v can dig  digit crystals  . : darkness  * glowmoss  ! unstable
row  0   5.    4: ! @2.    3.
row  1   4    v4.   v5:   v2
```

## Saves
`to_state()` adds `rules` (currently 2, bumped when an older save would replay differently). `Game.from_state()` checks the save before loading and raises `ValueError` naming the first problem: wrong game or rules version, unknown difficulty, a grid of the wrong shape or with out-of-range values, a position outside the shaft, more light than the lamp holds, or a path that does not end at the saved column.

## Helpers
- Hint: `g.hint()` is the first move of the best delve from where you stand (`("climb", 0)` when no dig adds crystals safely). Following hints from the surface digs exactly the demo's best delve.
- Seed codes: `seed_code(1337, "normal")` is `GLOW-N-1337`; `parse_seed_code(code)` reads one back (trimmed, any case) and raises `ValueError` saying what is wrong. The native core refuses codes with more than 9 seed digits (uint32 seeds).
- Daily shaft: `daily_seed(2026, 10, 30)` is `20261030`, so everyone delves the same shaft on the same day.
- Errors name the problem: the shaft floor, the columns you can reach, an unknown action, or a dig without a column number.

## API
Actions: `("dig", column)`, `("climb", 0)`. Default difficulty: normal. API: `g = glowmoss.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.glowmoss --play --difficulty normal --seed N`, `--demo --seed N` (digs the best delve, then climbs out).

## Tests
- `test_glowmoss.py`: the shared Prismheart contract, rules tests, and property sweeps (target always within the best delve and the demo always perfect, same seed same shaft, save/load round trip at every step, random legal digs keep the lamp and path consistent, greedy beats random).
- `glowmoss_core_test.cpp`: replays every fixture line (shafts, probes, every dig and hint) and sweeps 200 seeds per difficulty natively (determinism, seed code round trip, hint equals the best delve at every step, target within best, demo perfect).

## Daedalus tie-in
Below Prismheart's shard fields run crystal shafts lit only by lamps and the glowmoss that grows on some ledges; delvers bring up raw shard crystal for the Glimmerloom market. Placement: a Prismheart cave mouth beside the realm's arcade row. Source only for now: no cabinet, realm row, editor or Unreal assets; the Python module stays the rules authority. Original game by prism-shard-dev, Oct 30.
