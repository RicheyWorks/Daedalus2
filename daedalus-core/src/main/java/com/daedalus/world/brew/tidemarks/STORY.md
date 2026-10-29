# The Tide Marks: Youtube Master Island, chapter 90 (youtube-master, contest G466)

Chapters 1-89 run from melody brewing (G25) to the shell purse (G460) and the twin baskets (G463). Storm season is
near, and Keeper Oriel reads the sea wall for warnings.

## Story

The sea wall holds a long row of tide marks, one letter per high tide. Keeper Oriel asks how many different patterns
of a set length appear on the wall. Counting every stretch of wall is the trap, since a pattern that repeats is one
pattern. A WRONG count earns no credit, and a pattern longer than the wall is too SHORT a wall to read.

## Beats, mechanics and tests (`TideMarksTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The wall | `seeded`: 0-12 marks from a-c, pattern length 1-4 | `seededIsDeterministic` |
| Patterns | `distinct()`: Rabin-Karp rolling hash over every window, with hash matches checked letter by letter so a collision never merges two patterns; equals brute force with a set of substrings (30 seeds); `windows()` counts every stretch | `answerMatchesBruteForce` |
| Every stretch is a trap | wall ababa, length 2: 2 patterns, 4 stretches | `trap` |
| Wrong, short | `count` WRONG, MALFORMED, SHORT (wall ab, length 3), no credit | `wrongAndSpecialEarnNoCredit` |
| Wall rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_tide_marks` | colony `QuestProgress`: read marks x1, count patterns x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperTideMarks`)

- Greeting: "The sea wall reads ababa, one mark per high tide. How many different runs of 2 marks are on it?"
- Wrong: "Not 4. A run that comes back is still one run."
- Short: "The wall is shorter than the run. Nothing to read."
- Quest done: "Every pattern read! I know what the sea is saying."
- After: "The tide writes and the wall remembers."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A stone sea wall with carved tide marks in a row and a lantern on top. Source-only here.
