# Shardring Resonance (prism sphere shard minigame)

Module: `tools/minigames/prism_shard.py` (pure Python, stdlib, seeded). Tests: `tools/minigames/test_prism_shard.py`.

## Play
A cracked prism sphere has a ring of empty facets. Each turn one Prism Shard of a hue arrives (the next one is shown). Set it in any empty facet. Three or more facets of one hue in a row (the ring wraps) resonate and clear for run^2 x chain points; consecutive resonances raise the chain. Every third resonance of a hue summons that Warden's spirit: +25 and the spirit clears one more facet.

Game over: every facet is full (the sphere shatters, lost) or the shard pouch is empty (won).

| difficulty | facets | hues | shards |
|---|---|---|---|
| easy | 12 | 3 | 60 |
| normal (default) | 10 | 4 | 50 |
| hard | 8 | 5 | 40 |

API: `g = prism_shard.start(seed, "normal")`, `g.place(facet)`, `g.status()` (score, over, won, ring, spirits).

## Play mode, demo, save
- `python -m tools.minigames.prism_shard --play --difficulty normal --seed N`: text ring, type a facet number (q quits).
- `python -m tools.minigames.prism_shard --demo --seed N`: plays a full seeded game with the greedy helper; same seed, same output.
- `g.to_state()` returns a JSON-safe dict (v1, includes the RNG state); `ShardringGame.from_state(d)` resumes the game exactly. A host save slot can store it later.

## Realm cabinet
`data/minigames/realm-arcades.json` names `shardring` in `prismheart_realm`; `realm_cabinets.py` places it with host tag `PythonMinigame`, a crc32 seed, and difficulty `normal`. Python games are placed only when named explicitly, never by a glob. No Unreal actor runs Python games yet; that needs a native host (not in this change).

## Daedalus tie-in
Prismheart's Wardens each guard a hue of Prism Shard; resonating shards wakes their summon spirits (G09 lore). Intended as a shrine cabinet in Windmere. Source only; no Unreal cabinet yet.
