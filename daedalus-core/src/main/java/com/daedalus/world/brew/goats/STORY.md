# The Goat Leaps: Youtube Master Island, chapter 49 (youtube-master, contest G306)

Chapters 1-48 run from melody brewing (G25) to the name stones (G297) and the two buckets (G301). While the pickle
sets, a bleating comes from the cliff: a kid has strayed down the ledges.

## Story

The cliff is a grid of ledges, some crumbled. The old goat leaps like a knight, two ledges one way and one the other.
Keeper Oriel asks the player to guide her from the top-left ledge to the kid at the bottom-right in as few leaps as
possible. The fewest leaps is right; a longer route earns no credit, and a route over a crumbled ledge means a fall
and earns none. Some cliffs cannot be crossed at all.

## Beats, mechanics and tests (`GoatLeapsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The cliff | `seeded`: 3-7 by 3-7 ledges, 1 in 5 crumbled; a 2 by 2 cliff has no leap | `seededCliffIsDeterministic` |
| The fewest leaps | `fewest()`: breadth-first search over knight leaps; equals brute-force relaxation (30 seeds) | `fewestMatchesBruteForce` |
| Known cliffs | 4 by 4 with a crumbled ledge: 2 leaps; open 3 by 3 corner to corner: 4 | `knownCliff` |
| A fall | a leap onto a crumbled ledge: `leap` is FELL, no credit | `crumbledLedgeEarnsNoCredit` |
| Cliff rules | `leap`: NOT_THERE (not a knight leap), STRAY, DUPLICATE, IGNORED | `guards` |
| Quest `q_goat_leaps` | colony `QuestProgress`: spot kid x1, leap well x1 (LONG can be redone), talk keeper_oriel | `questLongThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperGoatLines`)

- Greeting: "A kid is stuck on the cliff, 4 ledges down and 4 across. The old goat leaps two one way and one the
  other. Get her there in as few leaps as you can, and mind the crumbled ledges."
- Fell: "That ledge is crumbled. She'd have slipped. Try another way."
- Stray: "She's still not beside the kid."
- Long: "4 leaps. She could do it in 2."
- Quest done: "Mother and kid together again. Listen to them bleat."
- After: "The goats are grazing on the cliff top."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A cliff face of ledges, some crumbled, a goat that arcs from ledge to ledge, and a kid at the bottom. Source-only here.
