# The Tide Pools: Youtube Master Island, chapter 39 (youtube-master, contest G266)

Chapters 1-38 run from melody brewing (G25) to the orchard rows (G258) and the sea wall (G262). With the storm board
up, the first winter rain comes in over the rock shelf below the wall.

## Story

The rock shelf is a row of rocks of different heights. When rain falls, every hollow fills up to the lower of the
tallest rocks on its two sides, and the rest runs off to sea. Keeper Oriel wants to know how much water the pools will
hold so the crabs stay wet until the tide returns. The player walks the shelf and names an amount. The exact amount is
right; any other reading is wrong and earns no credit.

## Beats, mechanics and tests (`TidePoolsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The shelf | `seeded`: 3-14 rocks, 0-9 high | `seededShelfIsDeterministic` |
| The pools | `held()`: trapped water by two pointers; equals a level-by-level brute force (30 seeds) | `heldMatchesBruteForce` |
| A known shelf | 0,1,0,2,1,0,1,3,2,1,2,1 holds 6; a rising shelf holds 0 | `knownShelfAndFlatShelf` |
| Wrong reading | any other amount: `read` is WRONG, no credit | `wrongReadingEarnsNoCredit` |
| Shelf rules | `read`: IGNORED, DUPLICATE | `guards` |
| Quest `q_tide_pools` | colony `QuestProgress`: walk shelf x1, read right x1 (WRONG can be retried), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperPoolLines`)

- Greeting: "12 rocks on the shelf. Rain is coming. Tell me how much water the pools will hold, so we know if the
  crabs stay wet till the tide."
- Wrong: "You said 5. The shelf held a different amount. Look again where the tall rocks stand."
- Quest done: "Exactly right. The crabs will be fine."
- After: "The pools are full. Mind your step."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A rock shelf below the sea wall, rain that fills each hollow to its water line, and crabs in the pools. Source-only
here.
