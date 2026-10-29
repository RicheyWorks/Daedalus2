# Wardens' Accord

Module: `tools/minigames/wardens_accord.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_wardens_accord.py`.

## Play
Each round the altar offers three seeded shards; take one into your pouch (costs the round). Any time, spend shards matching a spirit's cost to summon it for its value; a new spirit takes its place. Reach the target score before the rounds run out. Stdlib only, deterministic per seed.

| difficulty | hues | rounds | target | spirits |
|---|---|---|---|---|
| easy | 3 | 16 | 40 | 4 |
| normal | 4 | 14 | 50 | 4 |
| hard | 5 | 12 | 55 | 3 |

Default difficulty: normal. API: `g = wardens_accord.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.wardens_accord --play --difficulty normal --seed N` (text play), `--demo --seed N` (scripted, deterministic full game).

## Daedalus tie-in
The Wardens' altar trades their hued Prism Shards for the summon spirits of Prismheart lore (Cinder Wisp, Mere Sprite, Thornkin and more). Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only; no native host yet). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
