# DiskSaver Island: Byte Spring cistern (contest G39, quest `q_byte_spring`)

The Byte Spring wells up from a crack in the shattered planet on DiskSaver Island. It feeds a cistern,
and the cistern's "water" is the RAM and disk budget that keeps resident island caches streamed in
(the DSB 1 streaming budget, ADR-063). The spring leaks, the dry season is long, and every resident
island drinks its cost each tick. Spigot, the cistern-keeper, asks you to get the island through the
season without dropping the home cache.

Offline, deterministic and integers only. No Unreal, no wall clock, no floats, so a Java or C++ port can
replay `trace()` byte for byte (the test pins two SHA-256 golden traces).

## Rules (one tick)
1. Optional player action: `("load", id)` or `("unload", id)`. A refused action (unknown, duplicate,
   not resident, or unloading the keystone) raises `ByteSpringError` and changes nothing.
2. Budget: while resident cost > `budget_cap`, dump the lowest `priority` (then the highest cost, then id).
3. Water: a wet tick adds `spring_fill`, capped at `capacity` (the rest spills). A dry tick removes `leak`.
   Then the residents drink their total cost. The level never goes below 0.
4. Drought: `empty_streak` counts consecutive dry ticks that end with an empty cistern. Any wet tick
   resets it, even one that stays empty. Dry ticks that still hold water do not count.
5. Fail (first match wins): the `keystone` island was dumped (`keystone_dumped`), or
   `empty_streak >= drought_limit` (`drought`). A failure beats a win on the same tick.
6. Win: `ticks >= win_ticks` and the cistern holds water. If it is empty at `win_ticks`, play goes into
   overtime until it holds water (win) or the drought ends it (fail).
7. A finished quest is frozen: later ticks and actions are ignored.

Weather is seeded: `weather(seed, n, dry_permille)` is a 32-bit LCG (a=1664525, c=1013904223, top 16
bits mod 1000), so the same seed gives the same season on any port.

## Composes with DSB 1
`tools/streaming/dsb.py` is the DSB 1 parser and picker (Python = Java = C++). Byte Spring reuses it:
- `islands_from_dsb(rows, unit_kib=1024)`: each DSB row becomes an island whose cost is
  `ceil((ram + disk) / unit_kib)` water units.
- `pick_residents(rows, viewer, load_cm, unload_cm, ram_budget_kib)`: the DSB 1 nearest-first picker
  chooses which islands start resident.
- `config_from_dsb(text, base_cfg, ...)`: builds a quest from the real `data/islands/streaming.dsb`.
  The keystone is kept only if the picker streamed it in.

## Reuse
- `validate(cfg)`: strict `byte-spring-v1` parser. Unknown keys, bools posing as ints, bad ids and
  out-of-range numbers are all rejected.
- `tick`, `simulate`, `simulate_seeded`, `trace`: a resource-budget survival loop that any island can
  re-skin (a well, a battery bank, an ark's water tank).
- `npc_say(state, config)`: returns (key, line) for the NPC. Lines live in the JSON under `npc.lines`
  with the keys `start wet dry spill low dump win fail_drought fail_keystone`.
- `receipt(state, config)`: the quest result in G12 activity-receipt shape
  (`quest, activity, island, outcome, score, ...`). The score is the water kept, in permille of
  capacity, and counts only on a win.

## Files
- `tools/streaming/byte_spring.py`: the sim, plus a CLI:
  `python tools/streaming/byte_spring.py data/islands/disk-saver/byte-spring-v1.json --seed 39`
  (exit 0 won, 1 lost, 2 bad input)
- `tools/streaming/byte_spring_test.py`: 46 offline tests (validation, budget dumps, actions, win/fail
  edges, seeded determinism and goldens, DSB composition including the real manifest, NPC, receipt, CLI)
- `data/islands/disk-saver/byte-spring-v1.json`: the island's quest config. Over seeds 0-199,
  an idle season wins about 65% of the time. Unloading `cache_north` on tick 1 wins about 96%.
- CI: `.github/workflows/byte-spring.yml` ("Byte Spring cistern") runs these tests and the DSB 1
  parity tests on every PR that touches them.

## Daedalus
The quest belongs to DiskSaver Island's storage lane. Its receipt can feed the G12 ActivityRouter, so a
companion who helps keep the caches wet learns from the game. Unreal props (the spring and the cistern)
come later from the Unreal owner. This module is the rules core they will bind.
