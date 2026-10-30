# The Lantern Parade: Youtube Master Island, chapter 23 (youtube-master, contest G209)

Chapters 1-22 run from melody brewing (G25) to the water casks (G199) and the lost verse (G204). It is the last night
at the spring before the boats go on.

## Story

The Song School children walk the beach in a lantern parade so the other boats can see the camp. They stand in a
line, each with a lantern pole of a different height. Keeper Oriel wants every lantern a little higher than the one in
front, front to back. The player keeps children walking or sits them out on the sand; the order of the line can't
change. A parade that climbs and keeps the most children walking is bright; one that climbs with fewer is dim.

## Beats, mechanics and tests (`LanternParadeTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The line | `seeded`: 6-12 children with poles of height 1-15 | `seededLineIsDeterministic` |
| The longest climb | `longest()`: longest strictly increasing subsequence DP; equals brute force over every subset (30 seeds); `bestParade()` walks it back and rises | `longestMatchesBruteForce` |
| The tall one at the front | a 9 at the head blocks everyone; the best parade sits it out | `theTallestFirstLanternIsNotAlwaysKept` |
| Equal poles | equal heights don't climb: `march` returns NOT_RISING, no credit | `equalLanternsDoNotClimb` |
| Parade rules | `keep` / `seat` / `march`: UNKNOWN, ALREADY_KEPT, NOT_KEPT, EMPTY, DUPLICATE, IGNORED | `guards` |
| Quest `q_lantern_parade` | colony `QuestProgress`: keep child x3, march bright x1 (DIM can be fixed), talk keeper_oriel | `questDimThenBrightThenKeeper` |

## Keeper Oriel's lines (`KeeperParadeLines`)

- Greeting: "Each lantern a little higher than the one before, front to back, so the ships can see us climb. Keep as
  many walking as that allows."
- Lining up: "2 walking."
- Not rising: "2 walking, but someone's lantern doesn't climb. Sit them out."
- Dim: "It climbs, but only 2 walk where 4 could. Who's sitting out that needn't?"
- Quest done: "Every lantern higher than the last, and nearly everyone walking. Bright!"
- After: "The parade's done. Lanterns out, off to bed."

## Editor later (UNREAL-QUEUE)

Children in a line on the night beach with lantern poles of marked heights, a sit-out spot on the sand, and the
lanterns rising front to back as the parade walks. Source-only here.
