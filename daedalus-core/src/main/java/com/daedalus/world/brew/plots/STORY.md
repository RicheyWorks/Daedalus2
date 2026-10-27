# The Berry Patch: Youtube Master Island, chapter 61 (youtube-master, contest G360)

Chapters 1-60 run from melody brewing (G25) to the sea currents (G351) and the rope splicing (G357). While the boat
is away, the children go berry picking.

## Story

The berry patch is a grid of bushes, each with a count of ripe berries. Each child may pick one square plot. Keeper
Oriel asks where the square with the most berries is. The single richest bush may sit in a poor corner; a POOR square
earns no credit.

## Beats, mechanics and tests (`BerryPatchTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The patch | `seeded`: 1-7 by 1-7 bushes, 0-9 berries, a side that fits | `seededPatchIsDeterministic` |
| Counting fast | `sum(...)` from a 2D prefix table; every rectangle and `richest()` equal brute force (30 seeds) | `sumsAndRichestMatchBruteForce` |
| The big bush is a trap | the 9-berry corner square holds 13; the square at (1,1) holds 16 | `richestBushIsATrap` |
| Poor | `pick` a poorer square is POOR, no credit | `poorEarnsNoCredit` |
| Patch rules | `pick`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_berry_patch` | colony `QuestProgress`: count bushes x1, pick richest x1 (retries allowed), talk keeper_oriel | `questPoorThenRichestThenKeeper` |

## Keeper Oriel's lines (`KeeperBerryLines`)

- Greeting: "A patch of 3 by 3 bushes. Each child may pick one 2 by 2 square. Where is the square with the most
  berries?"
- Poor: "That square has 13 berries. One has 16."
- Quest done: "The richest square. Fill the baskets!"
- After: "Baskets full of berries for the jam."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A grid of berry bushes with string marking square plots, and children's baskets. Source-only here.
