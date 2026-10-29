# The Island Flags: Youtube Master Island, chapter 28 (youtube-master, contest G226)

Chapters 1-27 run from melody brewing (G25) to the shell strings (G219) and the ferry crossing (G223). The children
reach the outer isles, where each isle flies a flag so sailors know where they are.

## Story

The flags have faded and must be re-dyed. Isles that share a shore must fly different colours or sailors mistake one
for the other, and every pot of dye is dear. Keeper Oriel asks the player to dye each isle's flag and raise them all.
A set with no clashes at the fewest colours flies well. Neighbours in the same colour clash, and a clash-free set with
extra colours is wasteful; neither earns credit.

## Beats, mechanics and tests (`IslandFlagsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The isle map | `seeded`: 4-8 isles, each pair shares a shore with probability 1/2 | `seededMapIsDeterministic` |
| The fewest colours | `fewest()`: chromatic number by DP over subsets (independent colour classes); equals brute force over every colouring (30 seeds) | `fewestMatchesBruteForce` |
| The odd ring | a ring of 5 isles needs 3 colours, a ring of 4 needs 2 | `oddRingNeedsThree` |
| Clashing flags | neighbours in one colour: `raise` is CLASH, no credit | `clashEarnsNoCredit` |
| Dye rules | `dye` / `raise`: NOT_THERE, BAD_COLOUR, UNFINISHED, DUPLICATE, IGNORED | `guards` |
| Quest `q_island_flags` | colony `QuestProgress`: dye flag x1, raise well x1 (WASTEFUL can be re-dyed), talk keeper_oriel | `questWastefulThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperFlagLines`)

- Greeting: "4 isles, and no two that share a shore may fly the same colour. Dye as few cloths as you can."
- Dyeing: "2 of 4 isles flagged so far."
- Clash: "Isles 0 and 1 share a shore and the same colour. Sailors will be lost."
- Wasteful: "No clashes, but 4 colours where 2 would do. Dye is dear."
- Quest done: "Every isle its own from its neighbours, and not a pot of dye wasted."
- After: "The flags are up. Watch them in the wind."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A flag locker with dye pots, flagpoles on each isle of a harbour map table, and flags that change cloth colour when
dyed. Source-only here.
