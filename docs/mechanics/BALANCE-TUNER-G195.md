# Minigame Balance Tuner (G195)

Package: `daedalus-core/src/main/java/com/daedalus/world/odds/balance/` (source only, offline, reporting only).
Follows the G192 balance simulator (`BALANCE-SIM-G192.md`), which flagged every Shardring and Cairnwell mode.

The tuner suggests difficulty settings; it does **not** change either game. Tuning is for each game's owner.

## How it works

- `TunableGame` exposes a game's integer difficulty knobs (`Knob`: name, min, max, step), the values the source
  ships per mode (null for a mode the source lacks), and plays one session at any knob values with the game's own
  rules (the G192 adapters' `playConfig`).
- `BalanceTuner` scores every grid point with the same seeded sessions (`OddsRng.forTrial`, common random numbers,
  so the search is deterministic and points are compared on equal luck), then goes softest mode first. A point
  qualifies when its whole 95% Wilson interval (`Intervals.wilson`) lies inside the mode's band **and** wholly below
  the softer mode's interval (strict easy > normal > hard). Among qualifying points it takes the one nearest the
  shipped values (knob steps, L1); for a missing mode it anchors on the previous mode's pick. The pick is then
  re-confirmed on a fresh seed; up to 8 ranked candidates are tried before a mode is reported as not found.
- Runtime is bounded: `tune` refuses a run whose total sessions (grid x search trials + confirm runs) exceed the cap.
  The published report is ~1 s of CPU.
- `BalanceTuner.monotonic` checks a list of results for strict, non-overlapping easy > normal > hard.
- Bands are G192's defaults: easy 60-98%, normal 30-90%, hard 10-75%.

Run: `TunerReport.main` (seed 195, 300 search trials per grid point, 4000 confirm trials per mode).

## Sources and knobs

Constants re-checked against origin/main 04a164a1 (26 Oct 2026). Cairnwell has landed on main (PR #501) with the
same constants as branch commit 5420cb03; Shardring is still only on `grok/prism-shard-minigame` (35634971).

| Game | Knobs (grid) | Shipped |
|---|---|---|
| Shardring Resonance (`tools/minigames/prism_shard.py`, `DIFFICULTY`) | facets 8-16, hues 2-5, shards 20-60 step 10 | easy 12/3/60, normal 10/4/50, hard 8/5/40 |
| Cairnwell (`DaedalusDesktopCairnwellCore.h`, `Cols`/`Rows`/`DropEvery`) | cols 3-8, rows 4-10, dropEvery 6-28 step 2 | practice (Option 1, as easy) 4/6/28, normal (Option 0) 6/8/16, hard: none |

## Assumed player models

- **Shardring**: the source's own `greedy_move` helper, no slip (as G192's headline numbers).
- **Cairnwell**: endless well, a session wins at 20 sunk layers before the well fills; 6-tick reaction, one column
  slide per two ticks toward the lowest column, 25% chance per stone of aiming at a random column (G192 default).

Different player models move the numbers; re-run `BalanceTuner` with another adapter to check.

## Recommended settings (seed 195, confirm n=4000)

| Game | Mode | Shipped | Shipped win (G192) | Suggested | Win | 95% Wilson | Change |
|---|---|---|---|---|---|---|---|
| Shardring | easy | 12 facets / 3 hues / 60 shards | 52.8% | 14 / 3 / 60 | 69.4% | 67.9-70.8% | +2 facets |
| Shardring | normal | 10 / 4 / 50 | 2.0% | 10 / 3 / 50 | 38.1% | 36.6-39.6% | 4 -> 3 hues |
| Shardring | hard | 8 / 5 / 40 | 0.0% | 8 / 3 / 40 | 21.0% | 19.8-22.3% | 5 -> 3 hues |
| Cairnwell | easy (practice) | 4 cols / 6 rows / drop 28 | 100.0% | 4 / 4 / 28 | 96.0% | 95.4-96.6% | 6 -> 4 rows |
| Cairnwell | normal | 6 / 8 / 16 | 100.0% | 6 / 7 / 8 | 88.6% | 87.5-89.5% | 1 row less, falls twice as fast |
| Cairnwell | hard (new) | none | missing | 6 / 5 / 8 | 61.1% | 59.6-62.6% | new third well (Option 2) |

Monotonic check passes for both games: easy > normal > hard with non-overlapping intervals.

Notes:

- Shardring: near the shipped ring sizes and pouches, hue count is the knob that matters, so the nearest in-band
  point for normal and hard drops to 3 hues. Keeping 4+ hues needs a much larger ring or a much shorter pouch (for
  example 16 facets / 4 hues / 20 shards won 92% on the search run), which is further from the shipped design.
- Cairnwell: the careful player always reaches the lowest column at drop 16 or slower, so only a faster fall
  (drop 8) creates real risk. The practice well was harder than normal for sloppy players because it has fewer
  rows; the suggested ordering fixes that (practice 96.0% > normal 88.6% > hard 61.1%), and still keeps practice
  as the four-column, slow-fall well its hint text promises. Suggested hard well: `Option==2` -> 6 cols, 5 rows,
  `DropEvery` 8.

Tests: `BalanceTunerTest` (determinism with a fixed seed, known answer on a toy game, monotonic check, published
suggestions in band and monotonic, bounded runtime / session cap, knob validation).
