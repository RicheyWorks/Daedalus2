# The Rope Splicing: Youtube Master Island, chapter 60 (youtube-master, contest G357)

Chapters 1-59 run from melody brewing (G25) to the beach mats (G348) and the sea currents (G351). The boat needs one
long tow rope.

## Story

Rope lengths lie in a row on the rope walk, and each ends in a different thickness. Splicing two neighbouring pieces
takes work equal to the product of the outer ends and the joint. Keeper Oriel asks for the least work to make one
rope. Splicing left to right is not always least; a HEAVY answer earns no credit.

## Beats, mechanics and tests (`RopeSplicingTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The rope walk | `seeded`: 1-6 ropes with end thickness 1-9 | `seededWalkIsDeterministic` |
| Least work | `least()`: matrix-chain interval DP; equals the minimum over every bracketing (30 seeds) | `leastMatchesBruteForce` |
| Order matters | ends 40, 20, 30, 10, 30: least 26000, left to right 48000 | `orderMatters` |
| Heavy | `name` with more work than least is HEAVY, no credit | `heavyEarnsNoCredit` |
| Rope rules | `name`: DUPLICATE, IGNORED (blank id or negative) | `guards` |
| Quest `q_rope_splicing` | colony `QuestProgress`: lay ropes x1, name least x1 (retries allowed), talk keeper_oriel | `questHeavyThenLeastThenKeeper` |

## Keeper Oriel's lines (`KeeperSpliceLines`)

- Greeting: "3 rope lengths in a row, each ending in a different thickness. Splice neighbours until one rope is left.
  What is the least work it can take?"
- Heavy: "That's 27000 work. It can be done with 4500."
- Quest done: "Least work. That's a sailor's splice."
- After: "One long rope, ready for the boat."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A rope walk with rope lengths of different thickness laid end to end, a splicing fid, and the finished coil.
Source-only here.
