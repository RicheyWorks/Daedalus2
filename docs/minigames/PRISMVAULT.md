# Prismvault Weigh

Module: `tools/minigames/prismvault.py` (pure Python, stdlib, seeded; shared plumbing in `prism_common.py`). Tests: `tools/minigames/test_prismvault.py`.

## Play
One shard in the vault is hollow (lighter). Each weighing puts two equal, disjoint groups on the balance and tells you which side is lighter (or that it balances). When you are sure, name the hollow shard. A correct name scores 100 + 50 per unused weighing; a wrong name loses. Stdlib only, deterministic per seed.

| difficulty | shards | weighings |
|---|---|---|
| easy | 8 | 3 |
| normal | 12 | 3 |
| hard | 27 | 3 |

Default difficulty: normal. API: `g = prismvault.start(seed, "normal")`, `g.step(action)`, `g.status()`, `g.to_state()` / `Game.from_state(d)` (JSON-safe, RNG included).
CLI: `python -m tools.minigames.prismvault --play --difficulty normal --seed N` (text play), `--demo --seed N` (scripted, deterministic full game).

## Daedalus tie-in
A hollow forgery hides among the vault's Prism Shards; the Warden's balance finds it. Listed in the Prismheart realm cabinet row (`prismheart_realm`, host tag `PythonMinigame`, data only; no native host yet). Part of the Oct 29 Prismheart campaign by prism-shard-dev.
