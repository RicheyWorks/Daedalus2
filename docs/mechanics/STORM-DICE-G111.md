# G111 Storm Dice (OddsReaper Island inn)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/dice/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

The ark crews passed the long belt nights with two dice carved from storm-glass offcuts. The game
came ashore with them and the Odds Keeper still runs the table. He is honest about it: the pass line
keeps a small edge for the house, and behind a point he pays true odds, which keep no edge at all.
The crews who knew that lasted longest at his table.

| Story beat | Mechanic in code |
|---|---|
| Two storm dice | `DiceMath.ways` / `chance` (36ths), `StormDice.die` (seeded) |
| Come-out: 7 or 11 wins, 2/3/12 loses, else a point | `StormDice.play`, `DiceMath.isPoint` |
| The point must repeat before a 7 | `DiceMath.pointMade` = ways / (ways + 6) |
| "Pass line wins 244 in 495" | `DiceMath.passWinFraction`: exact rational, lowest terms |
| Behind a point the Keeper pays true odds (2:1, 3:2, 6:5) | `DiceMath.trueOdds`: zero expected value, tested per point |
| Full odds thins the house edge | `edgePerHerbWagered(m)`: 1.41% flat, 0.47% at 3x odds |
| The chalk checked against the dice | `StormDice.passWinEstimate`: seeded estimate with Wilson interval |

## Quest q_storm_dice

Pick 0 to 3 herbs of odds behind every point, then shoot 10 rounds.

1. AT_THE_TABLE: "Pass line wins 244 in 495. House keeps 1.41% of every herb; behind a point I pay true odds."
2. SHOT (full odds, passes): "Full odds: my edge is down to 0.47% a herb. W of 10 rounds won, +N herbs."
3. SHOT (less): "W of 10 rounds, +N herbs. You left free odds on my table."

Herbs are in-game only; there is no real-money gambling.

## Editor / asset needs (later, not in this PR)

- Dice table prop and two storm-glass dice; roll animation and bark.
