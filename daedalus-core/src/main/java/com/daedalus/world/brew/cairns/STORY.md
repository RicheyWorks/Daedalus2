# The Cairn Run: Youtube Master Island, chapter 104 (youtube-master, contest G489)

Chapters 1-103 run from melody brewing (G25) to the cargo weights (G486) and the regatta order (G487). The old hill
path is marked by numbered stone cairns, many of them toppled.

## Story

Keeper Oriel walks the hills and notes each standing cairn's number in the order found. The path can be rebuilt along
the longest run of consecutive numbers still standing, whatever order they were found in. Keeper Oriel asks how long
that run is. Looking only for numbers found one after another on the walk is the trap. A WRONG count earns no credit,
and a walk that finds NONE standing leaves nothing to rebuild.

## Beats, mechanics and tests (`CairnRunTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The walk | `seeded`: 0-8 cairn numbers 0-9 (repeats possible) | `seededIsDeterministic` |
| Longest run | `run()`: hash set of numbers; start counting only at a number with no predecessor, so each number is visited once; equals brute force extending from every number (30 seeds) | `answerMatchesBruteForce` |
| Walk order is a trap | found 5 1 3 2 9 4: run 1-5 is 5 long, walk order gives 1 | `trap` |
| Wrong, none | `count` WRONG, MALFORMED, NONE (no cairns found), no credit | `wrongAndSpecialEarnNoCredit` |
| Hill rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_cairn_run` | colony `QuestProgress`: read cairns x1, count run x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperCairnRun`)

- Greeting: "On the walk I found cairns numbered [5, 1, 3, 2, 9, 4], in that order. How long is the longest run of
  consecutive numbers still standing?"
- Wrong: "Not 1. The order I found them in doesn't matter, only which numbers stand."
- None: "Every cairn is down. No run to rebuild."
- Quest done: "The longest run! We'll rebuild the path along it."
- After: "Stone by stone, the hill path finds its way."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Grassy hills with numbered stone cairns, some standing and some toppled, along a faint path. Source-only here.
