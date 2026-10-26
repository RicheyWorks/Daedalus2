# G88 The Keeper's Tote (OddsReaper Island, Squall Cup day)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/tote/`.
Reuses `world.odds.OddsRng`. Takes the Keeper's chalked chances as input (for example G35 `CupOdds.chance`);
read-only on G35.

## Story

On Squall Cup day (G35) the inn is too full for the Keeper to chalk fixed odds for everyone, so he
runs a tote, the way the ark crews did: every herb goes into one pool, the house keeps its cut, and
the winners split the rest. The crowd sets the price with its hunches. The Keeper's chalk still
knows the truth, and a sharp player waits for the crowd to let a good runner drift.

| Story beat | Mechanic in code |
|---|---|
| One pool, the house keeps its cut, winners split the rest | `ToteBoard`: odds = pool x (1 - takeout) / stake on outcome; takeout capped at 25% |
| The crowd bets on hunches | `CrowdBets.fill`: each bettor skews the chalk by a seeded factor e^u and backs one outcome |
| Your own bet moves the price | `ToteBoard.oddsAfter` |
| How much can you put on before the overlay is gone? | `ToteBoard.maxOverlayStake`: closed form s < (p (1 - t) P - S_i) / (1 - p (1 - t)), checked against brute force |
| The Keeper nods at an overlay, frowns at a hunch | `ToteQuest.back` judges p x odds-after-stake > 1 |
| The heat is fished | `ToteQuest.race`: winner drawn from the fair chances on a fresh seeded stream |

## Quest q_keepers_tote

Crowd of 40 bettors x 5 herbs, 15% takeout.

1. BOARD_OPEN: "N herbs in the pool, 15% to the house. The crowd sets the price; my chalk sets the truth."
2. BACKED: overlay: "An overlay. The crowd let that one drift; you did not." Otherwise: "Under the chalk. You paid the crowd's price for the crowd's hunch."
3. WON: "Paid N herbs from the pool."
4. LOST: "Not this heat. A good price loses sometimes; a bad one loses for good."

Herbs are in-game only; there is no real-money wagering.

## Editor / asset needs (later, not in this PR)

- Tote board prop (rolling pool numbers) next to the G18 chalkboard.
