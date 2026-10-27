# The Lucky Doors: Youtube Master Island, chapter 83 (youtube-master, contest G440)

Chapters 1-82 run from melody brewing (G25) to the crab pens (G434) and the hut floor (G437). The village has grown
so long that every door now carries a number.

## Story

The doors along the shore street are numbered from 1. A door is lucky when its digits add up to the island's lucky
number, and every lucky door gets a painted shell. Keeper Oriel asks how many shells to paint, counting digit by digit
instead of door by door. Counting only the two-digit doors is a trap. A WRONG count or a bad pick earns no credit,
and if no door adds up to the lucky number the street has NO_LUCK.

## Beats, mechanics and tests (`LuckyDoorsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The street | `seeded`: 1-3000 doors, lucky sum 1-28 | `seededStreetIsDeterministic` |
| Lucky doors | `lucky()`: digit DP (sum so far, still pinned to the last door's digits); equals brute force door by door (30 seeds); 10^15 doors with sum 1 gives 16 | `luckyMatchesBruteForce` |
| Two digits is a trap | doors 1-250, sum 7: 21 lucky, not the 8 two-digit ones | `twoDigitDoorsOnlyIsATrap` |
| Wrong, no luck | `count` WRONG, MALFORMED, NO_LUCK (sum 30 on 250 doors), no credit | `wrongAndNoLuckEarnNoCredit` |
| Street rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_lucky_doors` | colony `QuestProgress`: walk street x1, count doors x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperLuckyDoors`)

- Greeting: "Doors numbered 1 to 250. A door is lucky when its digits add up to 7. How many lucky doors get a painted
  shell?"
- Wrong: "Not 8. Count again, digit by digit."
- No luck: "No door on this street adds up to that. No shells to paint."
- Quest done: "That many lucky doors! Fetch the paint."
- After: "Every lucky door wears a painted shell."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A shore street of numbered hut doors, some with painted shells hung on them, and paint pots. Source-only here.
