# Glimmerloom Ledger

Module: `tools/minigames/glimmerloom.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_glimmerloom.py`.

## Play
Each market day every shard hue has a price that drifts on a seeded tide. Buy and sell as you like (your satchel holds a limited count), then rest to open the next day. Each morning a Warden whispers a rumor about one hue's next move; rumors are usually true. On the last day everything is sold. Finish with a purse at or above the target to win; score is the final purse. Stdlib only, deterministic per seed.

| difficulty | hues | days | purse | target | satchel | truth | tax |
|---|---|---|---|---|---|---|---|
| easy | 3 | 12 | 100 | 130 | 20 | 0.85 | 0 |
| normal | 4 | 10 | 100 | 135 | 15 | 0.75 | 0 |
| hard | 5 | 8 | 100 | 110 | 12 | 0.7 | 1 |

Actions: `("buy", hue, n)`, `("sell", hue, n)`, `("rest", 0, 0)`. `truth` is the chance the rumor is right; `tax` is taken from each shard sold. Tomorrow's moves are rolled before the rumor, so the rumor speaks about real moves. Default difficulty: normal. API: `g = glimmerloom.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.glimmerloom --play --difficulty normal --seed N`, `--demo --seed N` (scripted, deterministic).

## Daedalus tie-in
The Glimmerloom is Prismheart's shard market, where traders weave hued Prism Shards into bolts of light; the Wardens' whispers move its prices. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
