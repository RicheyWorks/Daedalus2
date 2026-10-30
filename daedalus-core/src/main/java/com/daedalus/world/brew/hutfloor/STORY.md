# The Hut Floor: Youtube Master Island, chapter 82 (youtube-master, contest G437)

Chapters 1-81 run from melody brewing (G25) to the ring dance (G429) and the crab pens (G434). The crab money buys
reeds, and a new hut needs its floor covered.

## Story

The new hut floor is a grid of squares with roof posts standing on some of them. Every reed mat covers two squares
side by side. Keeper Oriel asks how many ways the mats can cover every bare square exactly once, so the pattern can
change each season. Counting layouts for a bare floor and ignoring the posts is a trap. A WRONG count or a bad pick
earns no credit, and a floor where the mats can never fit (even with an even number of squares) has NO_FIT.

## Beats, mechanics and tests (`HutFloorTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The floor | `seeded`: 1-5 rows, 1-4 wide, about one post in six squares | `seededFloorIsDeterministic` |
| Layouts | `ways()`: broken-profile bitmask DP row by row; equals brute force laying mats at the first bare square (30 seeds; bare 3x4 = 11) | `waysMatchBruteForce` |
| Bare floor is a trap | posts in two far corners leave 5 layouts, not 11 | `bareFloorCountIsATrap` |
| Wrong, no fit | `count` WRONG, MALFORMED, NO_FIT (two posts on squares of one colour), no credit | `wrongAndNoFitEarnNoCredit` |
| Floor rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_hut_floor` | colony `QuestProgress`: sweep floor x1, count layouts x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperHutFloor`)

- Greeting: "A new hut floor, 3 rows of 4 squares, with posts where you see #. Each reed mat covers two squares side
  by side. How many ways can we cover every bare square?"
- Wrong: "Not 11. Try laying them out again, row by row."
- No fit: "However we lay them, some square stays bare. The mats won't fit this floor."
- Quest done: "That many layouts! We'll change the pattern every season."
- After: "The reed mats lie snug round every post."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A new hut interior with roof posts and woven reed mats laid on the floor, a bundle of reeds by the door. Source-only.
