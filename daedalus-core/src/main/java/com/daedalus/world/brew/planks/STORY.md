# The Flood Planks: Youtube Master Island, chapter 96 (youtube-master, contest G476)

Chapters 1-95 run from melody brewing (G25) to the kin tree (G472) and the lantern switches (G474). Spring tides lift
the floating dock, plank by plank.

## Story

The floating dock is a row of planks. Each flood tide lifts a stretch of planks by a few hands. Keeper Oriel lists the
floods and asks how high the highest plank ends up. Adding every flood together is the trap, since floods over
different stretches never stack on one plank. A WRONG height earns no credit, and a CALM season with no floods leaves
nothing to measure.

## Beats, mechanics and tests (`FloodPlanksTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The dock | `seeded`: 1-8 planks, 0-5 floods over random stretches, rising 1-3 | `seededIsDeterministic` |
| Highest plank | `highest()`: segment tree of maxima with lazy range add (each flood touches O(log n) nodes); equals brute force adding every flood plank by plank (30 seeds) | `answerMatchesBruteForce` |
| Adding every flood is a trap | 5 planks, floods [0-1 +2], [3-4 +3], [1-3 +1]: highest 4, all floods 6 | `trap` |
| Wrong, calm | `count` WRONG, MALFORMED, CALM (no floods), no credit | `wrongAndSpecialEarnNoCredit` |
| Dock rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_flood_planks` | colony `QuestProgress`: read floods x1, count height x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperFloodPlanks`)

- Greeting: "The dock has 5 planks, and the floods were [[0, 1, 2], [3, 4, 3], [1, 3, 1]] (first plank, last plank,
  hands of rise). How high is the highest plank?"
- Wrong: "Not 6. Floods over different planks don't stack."
- Calm: "No floods this season. Every plank sits level."
- Quest done: "Right! I'll tie the boats to that one."
- After: "The tide rises and falls, and the dock rides it."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A floating plank dock with tide marks painted on its posts, some planks lifted higher than others. Source-only here.
