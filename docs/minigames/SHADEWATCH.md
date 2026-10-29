# Shadewatch Vigil

Module: `tools/minigames/shadewatch.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_shadewatch.py`.

## Play
Shades spawn at the far end of seeded lanes and creep one step toward the heart each turn. Each turn choose one: flare a lane (burns its front shade), kindle (store one light, up to 5), or nova (spend 3 light to burn every shade within 2 steps of the heart). A shade that reaches the heart costs a heart. Survive every turn to win. Score: 5 per shade burned, 1 per turn survived, 10 per heart left on a win. Stdlib only, deterministic per seed.

| difficulty | lanes | length | spawn | turns | hearts |
|---|---|---|---|---|---|
| easy | 2 | 6 | 0.45 | 20 | 3 |
| normal | 3 | 6 | 0.33 | 24 | 3 |
| hard | 4 | 6 | 0.28 | 28 | 3 |

`spawn` is the per-lane chance a shade appears each turn. Light starts at 1 (max 5); a nova costs 3 and reaches 2 steps. Default difficulty: normal. API: `g = shadewatch.start(seed, "normal")`, `g.step(("flare", lane))` / `("kindle", 0)` / `("nova", 0)`, `g.status()`, `g.to_state()` / `Game.from_state(d)`.
CLI: `python -m tools.minigames.shadewatch --play --difficulty normal --seed N`, `--demo --seed N` (a simple scripted watcher; it does not win every seed).

## Daedalus tie-in
When Prismheart's shards dim, shades creep toward the heart-crystal; Warden watchers hold the lanes with shard flares until dawn. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
