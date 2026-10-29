# Prismcairn Duel

Module: `tools/minigames/prismcairn.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_prismcairn.py`.

## Play
Seeded cairns of Prism Shards stand between you and a Warden. On your turn take 1 to `take_max` shards from one cairn; the Warden answers. Whoever lifts the last shard wins the round (+50, plus 5 per round left on a match win). Best of three rounds wins the match. Every round's opening is winnable; the Warden errs less on harder settings. Stdlib only, deterministic per seed.

| difficulty | cairns | take_max | max_height | slip | rounds |
|---|---|---|---|---|---|
| easy | 3 | 3 | 7 | 0.5 | 3 |
| normal | 4 | 3 | 9 | 0.25 | 3 |
| hard | 5 | 4 | 11 | 0.0 | 3 |

`slip` is the chance the Warden makes a random move instead of its best one. Default difficulty: normal. API: `g = prismcairn.start(seed, "normal")`, `g.step((cairn, take))`, `g.status()`, `g.to_state()` / `Game.from_state(d)`.
CLI: `python -m tools.minigames.prismcairn --play --difficulty normal --seed N`, `--demo --seed N` (perfect play, deterministic).

## Daedalus tie-in
Prismheart's Wardens test would-be shard keepers at the cairns; the one who lifts the last shard earns the Warden's respect. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
