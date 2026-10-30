# The Sweeper's Walk: Youtube Master Island, chapter 76 (youtube-master, contest G417)

Chapters 1-75 run from melody brewing (G25) to the lamplighter's round (G410) and the weak bridges (G415). After the
storm, sand lies over every path in the meeting yard.

## Story

The meeting yard has spots (the well, the drum, the oven, the gate) joined by sandy paths. Keeper Oriel asks for one
walk that sweeps every path exactly once, since a swept path must not be walked again. Starting at a spot with an even
number of paths is a trap. A BROKEN walk that jumps between paths, a walk that MISSED or repeats a path, or a bad
pick earns no credit, and if too many spots have an odd number of paths (or the paths don't all join) there is
NO_WALK.

## Beats, mechanics and tests (`SweepersWalkTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The yard | `seeded`: 2-5 spots, 1-6 paths (repeats allowed) | `seededYardIsDeterministic` |
| One walk? | `possible()`: Euler's rule (paths connected, zero or two odd spots); equals brute force over every order of the paths (30 seeds) | `possibleMatchesBruteForce` |
| Even start is a trap | round the square from spot 1 leaves the diagonal out of reach | `startingAtAnEvenSpotIsATrap` |
| Broken, missed, no walk | `sweep` MISSED (skip or repeat), MALFORMED, NO_WALK (four odd spots; loose paths), no credit | `brokenMissedAndNoWalkEarnNoCredit` |
| Yard rules | `sweep`: IGNORED, DUPLICATE | `guards` |
| Quest `q_sweepers_walk` | colony `QuestProgress`: look yard x1, sweep paths x1 (retries allowed), talk keeper_oriel | `questBrokenThenSweptThenKeeper` |

## Keeper Oriel's lines (`KeeperSweepersWalk`)

- Greeting: "4 spots and 5 sandy paths. Sweep every path exactly once in one walk; a swept path must not be walked
  again."
- Broken: "You'd have to jump from one path to another there. Walk, don't leap."
- Missed: "Every path once, no more, no less."
- No walk: "4 spots have an odd number of paths, or the paths don't all join. No single walk can do it."
- Quest done: "Every path swept, none twice. The yard shines!"
- After: "The paths are clean, broom back in the shed."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A sandy meeting yard with a well, drum, oven and gate joined by paths, and a sweeper with a palm broom. Source-only.
