# The Harvest Feasts: Youtube Master Island, chapter 32 (youtube-master, contest G238)

Chapters 1-31 run from melody brewing (G25) to the echo cave (G232) and the net mending (G235). With the boats out,
the island turns to the harvest.

## Story

Every family wants the village hall for its harvest feast, each over its own hours, and each feast brings its own
cheer. The hall holds one feast at a time, though one can start the hour another ends. Keeper Oriel keeps the hall
book and asks the player to book feasts and open the hall. The most cheer possible opens well. Overlapping bookings
clash, and a clash-free book with less cheer is dim; neither earns credit.

## Beats, mechanics and tests (`HarvestFeastsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hall book | `seeded`: 3-12 feasts within 24 hours, 1-6 hours long, 1-9 cheer | `seededBookIsDeterministic` |
| The most cheer | `most()`: weighted interval scheduling (sort by end, binary search, DP); equals brute force over every subset (30 seeds) | `mostMatchesBruteForce` |
| The big feast trap | one long feast (cheer 5) against two short ones (3 + 3) that touch end to start | `twoSmallFeastsCanBeatOneBig` |
| Overlaps | two clashing feasts booked: `open` is OVERLAP, no credit | `overlapEarnsNoCredit` |
| Book rules | `toggle` / `open`: STRUCK, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_harvest_feasts` | colony `QuestProgress`: book feast x1, open well x1 (DIM can be rebooked), talk keeper_oriel | `questDimThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperFeastLines`)

- Greeting: "3 families want the hall for their harvest feast, and it holds one at a time. Book the feasts that bring
  the most cheer."
- Overlap: "Feasts 0 and 1 both want the hall at once. Strike one."
- Dim: "5 cheer booked where 6 could be. Look at the book again."
- Quest done: "The hall never stood empty when it could have rung. Best harvest in years."
- After: "The hall is swept. Save me some pie."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A village hall with long tables, a hall book on a stand with hour slots, and harvest decorations that change per
booked family. Source-only here.
