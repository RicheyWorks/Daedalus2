# The Driftwood Cuts: Youtube Master Island, chapter 78 (youtube-master, contest G424)

Chapters 1-77 run from melody brewing (G25) to the sweeper's walk (G417) and the quiet elder (G420). A long plank of
driftwood washed up overnight, and a trader's boat is in the cove.

## Story

The trader pays shells for pieces of driftwood, and the price depends on each piece's length. Keeper Oriel asks how
to cut the whole plank for the most shells. Selling the plank whole, the biggest piece, is a trap. A CHEAP cut,
pieces of the WRONG_LENGTH, or a bad pick earns no credit, and if the trader gives nothing for any piece there are
NO_BUYERS.

## Beats, mechanics and tests (`DriftwoodCutsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The plank | `seeded`: length 1-8, prices 0-9 | `seededPlankIsDeterministic` |
| Best cut | `best()`: rod-cutting DP over the first piece; equals brute force over every set of cuts (30 seeds) | `bestMatchesBruteForce` |
| Whole plank is a trap | 4 long sells for 9; two 2s fetch 10 | `biggestPieceIsATrap` |
| Cheap, wrong length, no buyers | `cut` CHEAP, WRONG_LENGTH, MALFORMED, NO_BUYERS (all prices 0), no credit | `cheapWrongLengthAndNoBuyersEarnNoCredit` |
| Woodpile rules | `cut`: IGNORED, DUPLICATE | `guards` |
| Quest `q_driftwood_cuts` | colony `QuestProgress`: measure plank x1, cut pieces x1 (retries allowed), talk keeper_oriel | `questCheapThenBestThenKeeper` |

## Keeper Oriel's lines (`KeeperDriftwood`)

- Greeting: "A driftwood plank 4 long, and the trader's shell prices for each length of piece. Cut the whole plank
  for the most shells."
- Cheap: "Those pieces fetch 9 shells. Cut another way and they'd fetch 10."
- Wrong length: "Your pieces don't add up to the whole plank."
- No buyers: "The trader won't give a single shell for any piece. Keep it for firewood."
- Quest done: "The best cut! The trader's shells are ours."
- After: "The pieces are traded and the shells are in the jar."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A driftwood plank on sawhorses with a hand saw, cut pieces, and a trader's boat with a shell jar. Source-only here.
