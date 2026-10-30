# Facetlock Lattice

Module: `tools/minigames/facetlock.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_facetlock.py`.

## Play
The Prismheart vault lock is a square lattice of coloured facets, scrambled by seeded shifts. Each move slides one row left/right or one column up/down (wrapping). Restore the pattern (row r all hue r) within the move budget. A win scores 100 + 10 per unused move. Stdlib only, deterministic per seed.

| difficulty | size | scramble | spare |
|---|---|---|---|
| easy | 3 | 3 | 4 |
| normal | 4 | 5 | 4 |
| hard | 5 | 7 | 3 |

Default difficulty: normal. API: `g = facetlock.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.facetlock --play --difficulty normal --seed N` (text play), `--demo --seed N` (scripted, deterministic full game).

## Daedalus tie-in
The Prismheart shard vault is sealed by a facet lattice; restoring its hue rows opens the vault. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only; no native host yet). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
