# The Sea Wall: Youtube Master Island, chapter 38 (youtube-master, contest G262)

Chapters 1-37 run from melody brewing (G25) to the grain mill (G254) and the orchard rows (G258). The harvest is in,
and the island readies for winter storms.

## Story

The old sea wall is a row of stones of different heights. Keeper Oriel wants one storm board nailed flush against it:
the board may span any run of stones, but it cannot stand taller than the lowest stone it covers or the wind will rip
it off. The player measures the wall and fits a board. The biggest board possible fits well; a smaller one is small
and an overhanging one is refused. Neither earns credit.

## Beats, mechanics and tests (`SeaWallTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The wall | `seeded`: 3-14 stones, 1-9 high | `seededWallIsDeterministic` |
| The biggest board | `largest()`: largest rectangle in a histogram by monotonic stack; equals brute force over every span (30 seeds) | `largestMatchesBruteForce` |
| The tallest stone is a trap | 2, 1, 5, 6, 2, 3: the tallest stone alone covers 6, stones 2-3 at height 5 cover 10 | `tallestStoneIsNotBest` |
| Overhang | a board taller than a stone it spans: `fit` is OVERHANG, no credit | `overhangEarnsNoCredit` |
| Wall rules | `fit`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_sea_wall` | colony `QuestProgress`: measure wall x1, fit well x1 (SMALL can be re-cut), talk keeper_oriel | `questSmallThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperWallLines`)

- Greeting: "6 stones along the sea wall, all different heights. Cut one storm board to sit flush on them, as big as
  it can be, before winter."
- Overhang: "A board 5 high over stones 1 to 3 sticks up past stone 1. The wind will rip it off."
- Small: "It fits, but covers 6 where 10 could be covered. Cut a bigger one."
- Quest done: "Flush on the stones and as big as the wall allows. Let winter come."
- After: "The board is nailed up. Listen to the waves."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A stretch of uneven sea-wall stones, a storm board that scales to the chosen span and height, and spray against the
wall. Source-only here.
