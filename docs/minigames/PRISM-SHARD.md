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

## Browser version
Open `tools/minigames/web/shardring/index.html` in any browser (one file, no server, no downloads). Pick a seed and difficulty; click a facet, or use Left/Right + Enter/Space, keys 1-9/0 for facets 1-10, R to restart.
The page's `shardring-core` script ports the Python rules and CPython's `random.Random(str)` (SHA-512 seeding + MT19937 + `choice`), so the same seed and difficulty give the same shard sequence and game as `prism_shard.py`. `test_prism_shard_web.py` builds fixtures from Python (shard sequences, full greedy games, final state for 18 seed/difficulty cases) and checks them with `node tools/minigames/shard_web_test.js` (skipped if node is missing).

## Controller
The page reuses the shared DaedalusPad layer (`daedalus-server/src/main/resources/static/controllers/daedalus-pad.js`, the same module the Prismheart demo uses; see `docs/controllers.md`). It loads it by a repo-relative path and feature-detects `window.DaedalusPad`, so the page still works with mouse and keyboard when the module is absent; nothing is fetched from the network. Shardring only maps DaedalusPad's logical actions (`Shardring.PAD_ACTIONS`): D-pad / left stick (up/left = previous facet, down/right = next), confirm (A, or the family's confirm button) = set shard, menu (Start) = restart. Keyboard and pad share `Shardring.applyVerb`. `shard_pad_test.js` drives the real module with a fake standard gamepad. The pad module itself is unchanged.

## Native port parity (C++ / Unreal)
`data/minigames/shardring-parity-v1.json` (schema `daedalus.minigames.shardring_parity/v1`) is generated from `prism_shard.py` by `python tools/minigames/shard_parity.py`; `--check` (and `test_shard_parity.py` in CI) fails if it is stale. It never changes the rules: after a rules or balance change, rerun the generator and commit both.

- `rules`: hues, spirit names, difficulty table, run length, spirit cadence and bonus, and the RNG contract (CPython `random.Random(str)`: SHA-512 seeding, MT19937, `choice` via `getrandbits`; the web page's port is a reference).
- `cases`: 3 difficulties x seeds 0, 1, 42, 2024. Each has `rng_seed_string` (`shardring:<seed>:<difficulty>`), the first 64 raw `sequence` draws, every move (`facet`, `shard`, `gained`, `score`, `chain`, `spirit`, `ring_before`, `ring_after`, `next_current`, `next_next`, `pouch`), `to_state()` `snapshots` after moves 5 and 20, `final` status and `result`.

How a native port should use it:
1. Seed check: rebuild the RNG from `rng_seed_string` and match `sequence`.
2. Replay: start the case, assert `ring_before` and `shard`, call place(`facet`), assert every other move field; then assert `final` and `result`. Moves follow `policy` (greedy), but replaying the listed facets is enough.
3. Save/load: load each snapshot `state` (RNG state is CPython's `getstate()`: version, 625 words, gauss), replay the remaining moves, and match `final`.
A port can skip the SHA-512 seeding by loading the RNG from a snapshot, but full parity needs step 1.

## Realm cabinet
`data/minigames/realm-arcades.json` names `shardring` in `prismheart_realm`; `realm_cabinets.py` places it with host tag `PythonMinigame`, a crc32 seed, and difficulty `normal`. Python games are placed only when named explicitly, never by a glob. No Unreal actor runs Python games yet; that needs a native host (not in this change).

## Daedalus tie-in
Prismheart's Wardens each guard a hue of Prism Shard; resonating shards wakes their summon spirits (G09 lore). Intended as a shrine cabinet in Windmere. Source only; no Unreal cabinet yet.
