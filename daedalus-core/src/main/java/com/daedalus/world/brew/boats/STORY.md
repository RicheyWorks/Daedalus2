# The Two Boats: Youtube Master Island, chapter 20 (youtube-master, contest G194)

Chapters 1-19 run from melody brewing (G25) to the keepsake chests (G181) and the night watch (G186). After the
first night at sea the fleet makes its first landfall.

## Story

On the landing beach the cargo comes off the big boat and has to go on in two smaller ones for the shallow crossing
ahead. Keeper Oriel wants both boats riding level. The player loads each crate onto boat A or boat B (or moves it
across, or carries it back to the sand), then pushes off. If the weight difference is the smallest the cargo allows,
the crossing is level; otherwise one boat lists and the player has to shift something.

## Beats, mechanics and tests (`TwoBoatsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The cargo comes off | `seeded`: 6-10 crates of 1-20 stone | `seededLandfallIsDeterministic` |
| As level as it gets | `bestDifference()`: subset-sum DP up to half the total; equals brute force over every subset (30 seeds); `bestSplit()` walks the table back and achieves it | `bestDifferenceMatchesBruteForce` |
| Heaviest first isn't enough | heaviest crate onto the lighter boat leaves 4 apart; the DP finds 15/15 | `greedyHeaviestFirstIsNotAlwaysBest` |
| The anvil | an odd split can't be perfect; the best possible difference counts as level | `anOddTotalCanNeverBeExactlyLevel` |
| Loading rules | `load` / `unload` / `cross`: UNKNOWN, MOVED, NOT_LOADED, ASHORE, DUPLICATE, IGNORED | `guards` |
| Quest `q_two_boats` | colony `QuestProgress`: load crate x4, cross level x1 (LISTING can be fixed, no credit), talk keeper_oriel | `questListingThenLevelThenKeeper` |

## Keeper Oriel's lines (`KeeperBoatLines`)

- Greeting: "Two boats, one pile of cargo. Split it so neither one sits low in the water."
- Loading: "4 crates still on the sand. A carries 8, B carries 0."
- Ready: "Everything's aboard. Push off when you're happy with it."
- Listing: "She's listing: 6 stone between them where 0 would do. Shift something."
- Quest done: "Both boats riding level. The crossing will be kind to us."
- After: "Load them like that every landfall."

## Editor later (UNREAL-QUEUE)

Two hulls at the waterline with a tilt gauge between them, crates on the sand that can be carried to either boat,
and the boats settling level (or listing) as they push off. Source-only here.
