# The Stage Bookings: Youtube Master Island, chapter 97 (youtube-master, contest G478)

Chapters 1-96 run from melody brewing (G25) to the lantern switches (G474) and the flood planks (G476). The festival
has one stage, and every band wants it.

## Story

Bands ask for the festival stage from one hour to another, each offering coins for the slot. Only one band can play at
a time, though one may start the hour another ends. Keeper Oriel asks for the most coins the stage can earn. Always
taking the band that finishes first is the trap: it fits the most bands, not the most coins. A WRONG total earns no
credit, and with no bookings at all the stage is EMPTY.

## Beats, mechanics and tests (`StageBookingsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The requests | `seeded`: 0-7 bookings, start 0-8, length 1-4, coins 1-9 | `seededIsDeterministic` |
| Most coins | `best()`: weighted interval scheduling (sort by end, best[i] = max(skip, coins + best of the last booking ending by its start, found by binary search)); equals brute force over every subset (30 seeds), and the greedy never beats it | `answerMatchesBruteForce` |
| Finishing first is a trap | [0-2 for 1], [1-5 for 10], [3-6 for 2]: best 10, earliest-finish greedy 3 | `trap` |
| Wrong, empty | `count` WRONG, MALFORMED, EMPTY (no bookings), no credit | `wrongAndSpecialEarnNoCredit` |
| Stage rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_stage_bookings` | colony `QuestProgress`: read bookings x1, count coins x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperStageBookings`)

- Greeting: "The bands ask for the stage: [[0, 2, 1], [1, 5, 10], [3, 6, 2]] (start, end, coins). One band at a time.
  What is the most the stage can earn?"
- Wrong: "Not 3. Fitting the most bands isn't the same as earning the most coins."
- Empty: "No band asked for the stage. Nothing to earn."
- Quest done: "The most coins! The festival chest is full."
- After: "The music plays, one band after another."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A wooden festival stage with bunting, a chalk booking board and a coin chest beside it. Source-only here.
