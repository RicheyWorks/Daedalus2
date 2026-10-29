# The Flag Shells: Youtube Master Island, chapter 86 (youtube-master, contest G453)

Chapters 1-85 run from melody brewing (G25) to the refrain count (G443) and the lantern wishes (G448). After the
festival the children want to hang the island flag, made of shells, by the meeting yard.

## Story

The flag is a line of shells: all the reds, then the whites, then the blues. The children laid them in a muddle.
Each move swaps any two shells, and Keeper Oriel asks for the fewest moves. One move per misplaced shell is a trap,
since a good swap fixes two. A WRONG count or a bad pick earns no credit, and a line that is ALREADY_FLAG needs no
moves at all.

## Beats, mechanics and tests (`FlagShellsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The line | `seeded`: 1-8 shells of R, W, B; `sorted()` by one Dutch national flag pass | `seededLineIsDeterministic` |
| Fewest swaps | `fewest()`: count misplaced shells per (place, colour); direct trades cost 1, each leftover three-way cycle 2; equals brute force breadth-first search over swaps (30 seeds) | `fewestMatchesBruteForce` |
| One per shell is a trap | BWRWRB has 4 misplaced but needs 2; BRW needs 2 | `onePerMisplacedShellIsATrap` |
| Wrong, already flag | `count` WRONG, MALFORMED, ALREADY_FLAG (RWWB), no credit | `wrongAndAlreadyFlagEarnNoCredit` |
| Wall rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_flag_shells` | colony `QuestProgress`: lay shells x1, count swaps x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperFlagShells`)

- Greeting: "The shells lie BWRWRB. The flag is reds, then whites, then blues. Each move swaps two shells. What is
  the fewest moves?"
- Wrong: "Not 4. Trade pairs first, then fix the three-way muddles."
- Already flag: "These shells already make the flag. Nothing to swap."
- Quest done: "Fewest swaps! The flag shells shine on the wall."
- After: "The flag of shells hangs proud by the meeting yard."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A wooden flag board by the meeting yard with red, white and blue shells set in rows, children sorting shells. Source-only.
