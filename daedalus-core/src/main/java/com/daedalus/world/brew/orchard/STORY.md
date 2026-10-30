# The Orchard Rows: Youtube Master Island, chapter 37 (youtube-master, contest G258)

Chapters 1-36 run from melody brewing (G25) to the bakehouse (G248) and the grain mill (G254). With bread and flour
in, the children go up to the orchard for the last of the apples.

## Story

The apple trees stand in one long row. Keeper Oriel lets the children strip any tree bare, but never two side by
side, so the bees always have a neighbouring tree. The player strips trees (or hangs apples back) and carries the
basket in. The most apples possible carries well. Two bare neighbours, or a lighter basket, earn nothing.

## Beats, mechanics and tests (`OrchardRowsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The row | `seeded`: 3-14 trees with 0-12 apples | `seededRowIsDeterministic` |
| The most apples | `most()`: maximum non-adjacent sum by a take/skip DP; equals brute force over every subset (30 seeds) | `mostMatchesBruteForce` |
| Every other tree is a trap | 2, 9, 1, 1, 9: trees 1 and 4 give 18, every other tree from 0 gives 12 | `everyOtherTreeIsNotAlwaysBest` |
| Bare neighbours | two side-by-side trees stripped: `carry` is NEIGHBOURS, no credit | `neighboursEarnNoCredit` |
| Orchard rules | `toggle`: LEFT, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_orchard_rows` | colony `QuestProgress`: strip tree x1, carry well x1 (LIGHT can be fixed), talk keeper_oriel | `questLightThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperOrchardLines`)

- Greeting: "5 trees in the row. Strip any you like, but never two side by side, or the bees have nowhere to go.
  Bring back the most apples."
- Picking: "2 apples in the basket so far."
- Neighbours: "Trees 0 and 1 stand side by side and both are bare. The bees are cross."
- Light: "12 apples where 18 could be. Look along the row again."
- Quest done: "A full basket, and the bees still have their trees. Well picked."
- After: "The baskets are in the cellar. Mind the wasps."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A row of apple trees with apple clusters that can be stripped, a basket, and beehives at the row's end.
Source-only here.
