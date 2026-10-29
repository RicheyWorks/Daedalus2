# Shardfall Gamble

Module: `tools/minigames/shardfall.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_shardfall.py`.

## Play
Each round opens a seeded seam bag of valued shards and a few cracked ones. Draw to grow the round's pot; drawing the second cracked shard collapses the seam and loses the pot. Bank to add the pot to your score and open the next round. Reach the target by the last round. The bag's remaining counts are always shown. Stdlib only, deterministic per seed.

| difficulty | rounds | target | cracked | values |
|---|---|---|---|---|
| easy | 6 | 40 | 2 | 12 valued |
| normal | 5 | 40 | 3 | 12 valued |
| hard | 4 | 32 | 4 | 12 valued |

Default difficulty: normal. API: `g = shardfall.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.shardfall --play --difficulty normal --seed N` (text play), `--demo --seed N` (scripted, deterministic full game).

## Daedalus tie-in
Shards fall glowing from Prismheart's seams; greed cracks the seam. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only; no native host yet). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
