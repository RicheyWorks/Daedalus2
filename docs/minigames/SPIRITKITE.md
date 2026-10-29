# Spiritkite Weave

Module: `tools/minigames/spiritkite.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_spiritkite.py`.

## Play
The sky isles form a seeded graph; each wind lane between two isles costs wind. Fly lane by lane from the anchor isle (0), gathering each isle's spirit lantern the first time you land there, then land back at the anchor. If the kite can no longer reach the anchor with the wind left, it is lost. Land with lanterns worth at least the target to win (score = lanterns + unused wind). Every target is reachable: it is a share of the best possible round trip. Stdlib only, deterministic per seed.

| difficulty | isles | wind | share |
|---|---|---|---|
| easy | 7 | 30 | 0.6 |
| normal | 8 | 28 | 0.75 |
| hard | 10 | 26 | 0.9 |

`share` is the fraction of the best possible round-trip lantern total (exact subset search) that the target asks for. Default difficulty: normal. API: `g = spiritkite.start(seed, "normal")`, `g.step(("fly", isle))` / `g.step(("land", 0))`, `g.status()`, `g.to_state()` / `Game.from_state(d)`.
CLI: `python -m tools.minigames.spiritkite --play --difficulty normal --seed N`, `--demo --seed N` (follows the optimal tour).

## Daedalus tie-in
Prismheart's summon spirits ride kites between the sky isles carrying lanterns of shard light; the anchor isle is where the Prism Skiff moors. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
