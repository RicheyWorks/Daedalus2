# Minigame Balance Simulator (G190)

Package: `daedalus-core/src/main/java/com/daedalus/world/odds/balance/` (source only, offline, no game changes).

A seeded difficulty balance check for the minigames. Each game plugs in through a small `BalanceGame` adapter that
mirrors the game's real rules and difficulty constants and plays one session on `OddsRng`. `BalanceCheck` plays
`trials` sessions per difficulty (trial `t` uses `OddsRng.forTrial`, so the report does not depend on run order),
puts a 95% Wilson interval (`Intervals.wilson`) on each win rate and flags:

| Flag | Meaning |
|---|---|
| `TOO_HARD` | the whole interval is below the mode's band floor |
| `TOO_EASY` | the whole interval is above the mode's band ceiling |
| `NOT_MONOTONIC` | a harder mode's interval sits wholly above a softer mode's interval |
| `MISSING_MODE` | the difficulty was asked for but the game's source does not ship it |

Default bands (configurable per difficulty with `BalanceCheck.band`): easy 60-98%, normal 30-90%, hard 10-75%, other
names 10-95%. Run the report with `BalanceReport.main` (seed 190, 4000 trials per mode). To add a minigame, write an
adapter and list it in `BalanceReport.games()`.

## Sources read

Neither game is on `main` yet (checked origin/main 22ba3f5e, 26 Oct 2026); the rules come from their open branches.

- **Shardring Resonance**: `tools/minigames/prism_shard.py` on `grok/prism-shard-minigame` (35634971). easy 12
  facets/3 hues/60 shards, normal 10/4/50, hard 8/5/40; run of 3 clears for run^2 x chain; every 3rd resonance of a
  hue +25 and one random facet clears; full ring loses, empty pouch wins. Player: the source's own `greedy_move`.
  The Java port was cross-checked against the Python module itself (3000 seeds, same greedy player): 53.0% / 2.3% /
  0.07% there versus 52.8% / 2.0% / 0.0% here; the RNG differs, so per-seed games differ but the rates match.
- **Cairnwell**: `DaedalusDesktopCairnwellCore.h` on `cursor/cairnwell-20261026` (5420cb03). Option 0 (normal):
  6 columns, 8 rows, auto-drop every 16 ticks. Option 1 (practice, used as easy): 4 columns, 6 rows, every 28 ticks.
  No third option exists. The well is endless, so a session is a win at 20 layers before the well fills. Player:
  6-tick reaction, one slide per two ticks toward the lowest column, and a 25% chance per stone of aiming at a random
  column instead.

## Findings (seed 190, 4000 trials per mode)

| Game | Mode | Win rate | 95% Wilson | Mean score | Flags |
|---|---|---|---|---|---|
| Shardring | easy | 52.8% | 51.2-54.3% | 206.2 | TOO_HARD |
| Shardring | normal | 2.0% | 1.6-2.5% | 36.3 | TOO_HARD |
| Shardring | hard | 0.0% | 0.0-0.1% | 9.9 | TOO_HARD |
| Cairnwell | easy (practice) | 100.0% | 99.8-100% | 2804.0 | TOO_EASY |
| Cairnwell | normal | 100.0% | 99.9-100% | 3208.1 | TOO_EASY |
| Cairnwell | hard | not in source | | | MISSING_MODE |

Sensitivity:

- Shardring with a 10% random-move slip: 44.6% / 1.4% / 0.1%. Normal and hard are nearly unwinnable even for the
  source's own greedy helper; the ring fills long before the pouch empties.
- Cairnwell at 50% slip: easy 94.2%, normal 99.3% (normal flagged NOT_MONOTONIC). At 75% slip: easy 55.3%, normal
  78.1% (NOT_MONOTONIC again). The practice well is *harder* than the normal well for a sloppy player, because it has
  6 rows against 8, and more rows outweigh the extra columns. Any player who can see the lowest column has time to
  reach it in both wells, so a careful player never loses.

These are reports only. The games are unchanged; tuning is for each game's owner.
