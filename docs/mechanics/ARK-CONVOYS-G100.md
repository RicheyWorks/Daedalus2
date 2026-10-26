# G100 Ark Convoys (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/convoy/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained loss model; read-only on everything else.
Not G24 (drydock), G29 (cargo), G43 (seed vault) or G47 (single-ark routes).

## Story

The last six arks off the shattered surface had one argument the night before launch: sail
together, so crews could tow and patch each other, or split up, so one belt storm could not take
them all? Four had to land to seed the island. The Odds Keeper settled it with chalk, and he still
tells the story by setting the same puzzle.

| Story beat | Mechanic in code |
|---|---|
| A belt storm hits a whole convoy at once | `ConvoyRisk.shock` (30%) per convoy; separate convoys meet separate storms |
| Each ark can still be lost on its own | `lossCalm` 10% / `lossStorm` 60% per ark |
| Crews that sail together tow and patch each other | `aidCut`: 25% off loss chances per extra ark, capped at 45% |
| The Keeper chalks every split | `ConvoyPlan.arrivals` (exact convolution of storm/no-storm binomial mixtures), `atLeast`, `splits` |
| Chalk checked against the old logs | `ConvoyPlan.simulate`: seeded Monte Carlo with Wilson interval |
| Four must land | `ConvoyQuest` (q_convoy_split) |

On OddsReaper Island's numbers the best split is two convoys of three (about 94% that four land):
better than all six together (one storm can sink the plan) and much better than six lone arks (no aid).

## Quest q_convoy_split

1. PLANNING: "Six arks, four must land. Best chalk: [3, 3] at 94%. Together for aid, apart against the storm."
2. CHOSEN: within 1 point of the best: "[3, 3]. The old captains would have split it the same." Otherwise: "<split> gives N%; the chalk had N%."
3. SEEDED: "N arks landed. The island will grow again."
4. SHORT: "Only N landed. The belt kept the rest."

No wagering here: the quest grades the captain's split.

## Editor / asset needs (later, not in this PR)

- Convoy planning table at the inn (six ark tokens); launch bell bark.
