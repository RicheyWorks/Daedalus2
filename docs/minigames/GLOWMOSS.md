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

## API
Actions: `("dig", column)`, `("climb", 0)`. Default difficulty: normal. API: `g = glowmoss.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.glowmoss --play --difficulty normal --seed N`, `--demo --seed N` (digs the best delve, then climbs out).

## Daedalus tie-in
Below Prismheart's shard fields run crystal shafts lit only by lamps and the glowmoss that grows on some ledges; delvers bring up raw shard crystal for the Glimmerloom market. Placement: a Prismheart cave mouth beside the realm's arcade row. Source only for now: no cabinet, realm row, editor or Unreal assets; the Python module stays the rules authority. Original game by prism-shard-dev, Oct 30.
