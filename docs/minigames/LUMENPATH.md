# Lumenpath Refraction

Module: `tools/minigames/lumenpath.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_lumenpath.py`.

## Play
A beam of prism light enters the lattice from the west edge. Each move toggles one cell's shard mirror (empty -> / -> \ -> empty). The beam reflects off mirrors, passes through crystals (lighting them) and stops at cracked stone. Light every crystal before the moves run out. Each newly lit crystal scores 10; a win adds 20 per unused move. Stdlib only, deterministic per seed.

| difficulty | size | crystals | stones | moves |
|---|---|---|---|---|
| easy | 5 | 2 | 0 | 12 |
| normal | 6 | 3 | 2 | 10 |
| hard | 7 | 4 | 4 | 9 |

Default difficulty: normal. API: `g = lumenpath.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.lumenpath --play --difficulty normal --seed N` (text play), `--demo --seed N` (scripted, deterministic full game).

## Daedalus tie-in
Prismheart's crystal lattices wake when prism light reaches them; the same Prism Shards Wardens guard are cut into mirrors. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only; no native host yet). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
