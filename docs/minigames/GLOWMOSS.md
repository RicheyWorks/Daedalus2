# Glowmoss Delve

Module: `tools/minigames/glowmoss.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_glowmoss.py`. Native core: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusGlowmossCore.h` (header-only C++17 on `DaedalusPyRandomCore.h`), byte-checked against `engines/unreal/core-test/glowmoss_parity.txt` by `glowmoss_core_test.cpp`; regenerate the fixture with `python tools/minigames/glowmoss_parity.py` (`--check` in CI).

## Play
The shaft is a seeded grid of ledges, row 0 at the top; each ledge holds 1-5 crystals, has a darkness of 0-2 and may carry glowmoss. From the surface you dig down one row at a time onto a ledge at most one column left or right of where you stand. A dig burns `1 + darkness` light and gathers the ledge's crystals; glowmoss then refills the lamp by `refill`, never above its capacity. Climbing out from row r costs `(r + 2) // 2` light, so if a dig leaves less than that the lamp gutters and the delve is lost. Climb out with crystals at or above the target to win (score = crystals + light left). The target is `target_pct` percent of the best possible delve (exact DP over row, column and light), so every target is reachable. All rules math is integer.

| difficulty | cols | rows | light | refill | moss_pct | target_pct |
|---|---|---|---|---|---|---|
| easy | 3 | 8 | 12 | 4 | 25 | 60 |
| normal | 4 | 10 | 11 | 3 | 18 | 75 |
| hard | 5 | 12 | 10 | 3 | 12 | 90 |

Actions: `("dig", column)`, `("climb", 0)`. Default difficulty: normal. API: `g = glowmoss.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.glowmoss --play --difficulty normal --seed N`, `--demo --seed N` (digs the best delve, then climbs out).

## Daedalus tie-in
Below Prismheart's shard fields run crystal shafts lit only by lamps and the glowmoss that grows on some ledges; delvers bring up raw shard crystal for the Glimmerloom market. Placement: a Prismheart cave mouth beside the realm's arcade row. Source only for now: no cabinet, realm row, editor or Unreal assets; the Python module stays the rules authority. Original game by prism-shard-dev, Oct 30.
