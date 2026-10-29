# The Marsh Path: Youtube Master Island, chapter 92 (youtube-master, contest G470)

Chapters 1-91 run from melody brewing (G25) to the tide marks (G466) and the chore days (G468). The festival reeds
grow on the far side of the marsh.

## Story

The marsh is a grid of firm tussocks and deep pools. Keeper Oriel starts at the near corner and needs the reeds at
the far corner, stepping one tussock at a time (north, south, east or west, never into a pool). Keeper Oriel asks for
the fewest steps. The straight-line count is the trap, since pools force the path to wind. A WRONG count earns no
credit, and a marsh where the far corner can't be reached leaves Keeper Oriel SUNK.

## Beats, mechanics and tests (`MarshPathTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The marsh | `seeded`: 2-3 rows, 2-4 columns, about a quarter pools, corners firm | `seededIsDeterministic` |
| Fewest steps | `steps()`: A* search with the Manhattan distance as an admissible heuristic; equals brute force over every simple path (30 seeds), and `straight()` never exceeds it | `answerMatchesBruteForce` |
| A straight line is a trap | a winding 5x3 marsh: 10 steps, straight line 6 | `trap` |
| Wrong, sunk | `count` WRONG, MALFORMED, SUNK (pools cut off the far corner), no credit | `wrongAndSpecialEarnNoCredit` |
| Marsh rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_marsh_path` | colony `QuestProgress`: read marsh x1, count steps x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperMarshPath`)

- Greeting: "The marsh reads [..., ~~., ..., .~~, ...], with . for tussocks and ~ for pools. From the near corner to the
  far corner, what is the fewest steps?"
- Wrong: "Not 6. The pools won't let you walk a straight line."
- Sunk: "The pools cut off the far corner. No path to count."
- Quest done: "Fewest steps! My boots are barely wet."
- After: "The reeds are cut and the tussocks remember your path."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A misty marsh of grassy tussocks between dark pools, with a reed bed in the far corner. Source-only here.
