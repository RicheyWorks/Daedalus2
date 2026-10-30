# The Well Pipes: Youtube Master Island, chapter 45 (youtube-master, contest G289)

Chapters 1-44 run from melody brewing (G25) to the low tide walk (G278) and the water channels (G282). The cistern
is full, and the villagers start piping water between their wells.

## Story

Clay pipes are laid one at a time between the island's wells. Wells joined by any run of pipe share their water.
Keeper Oriel wants to know how many separate well groups are left, so the lonely ones can be watched in a dry spell.
The player walks the pipe lines and names a count. The exact count is right; any other count earns no credit. Some
pipes join wells that were already joined, so subtracting the pipes from the wells is a trap.

## Beats, mechanics and tests (`WellPipesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The wells | `seeded`: 2-12 wells, 0-14 pipes | `seededIslandIsDeterministic` |
| The groups | `groupsAfter(k)`: union-find with path halving and union by size; equals a brute-force flood fill after every pipe (30 seeds) | `groupsMatchBruteForceAfterEveryPipe` |
| The loop is a trap | 6 wells, 4 pipes with a loop: 3 groups, not 2; one pipe wasted | `loopPipeIsWasted` |
| Wrong count | any other number: `count` is WRONG, no credit | `wrongCountEarnsNoCredit` |
| Well rules | `count`: DUPLICATE, IGNORED | `guards` |
| Quest `q_well_pipes` | colony `QuestProgress`: walk pipes x1, count right x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperWellLines`)

- Greeting: "6 wells and 4 clay pipes laid between them. Wells joined by any run of pipe share their water. How many
  separate groups are left?"
- Wrong: "You count 2. Walk the pipes again: some join wells that were already joined."
- Quest done: "That's the count. Now we know which wells to watch in a dry spell."
- After: "The wells are mapped. Drink up."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Wells across the village with clay pipes that appear in the order laid, and water levels that even out across each
joined group. Source-only here.
