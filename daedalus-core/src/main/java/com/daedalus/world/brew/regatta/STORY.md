# The Regatta Order: Youtube Master Island, chapter 103 (youtube-master, contest G487)

Chapters 1-102 run from melody brewing (G25) to the jar shelves (G484) and the cargo weights (G486). The autumn
regatta sets off from the harbour in numbered order.

## Story

The boats start in number order and cross the line in a new order. Keeper Oriel asks how many pairs of boats swapped
places, meaning a higher-numbered boat finished ahead of a lower-numbered one. Counting only the boats that finished
right behind a higher number is the trap, since swaps far apart in the order count too. A WRONG count earns no credit,
and boats that finish IN_ORDER have swapped nothing.

## Beats, mechanics and tests (`RegattaOrderTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The finish | `seeded`: 1-8 distinct boat numbers 0-9 in finishing order | `seededIsDeterministic` |
| Swapped pairs | `swapped()`: merge sort counting inversions (each time the right half's boat is taken first, it passes every boat left in the left half); equals brute force over every pair (30 seeds) | `answerMatchesBruteForce` |
| Neighbours only is a trap | finish 3 1 2: 2 swapped pairs, 1 neighbour swap | `trap` |
| Wrong, in order | `count` WRONG, MALFORMED, IN_ORDER (finish 0 1 2), no credit | `wrongAndSpecialEarnNoCredit` |
| Regatta rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_regatta_order` | colony `QuestProgress`: read finish x1, count swaps x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperRegattaOrder`)

- Greeting: "The boats started in number order and finished [3, 1, 2]. How many pairs of boats swapped places?"
- Wrong: "Not 1. Boats far apart in the finish can have swapped too."
- In order: "They finished just as they started. Nothing swapped."
- Quest done: "Every swap counted! The race judges agree."
- After: "Sails down, and the harbour cheers every boat."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Small numbered sailing boats crossing a buoy finish line in the harbour, with a judges' platform. Source-only here.
