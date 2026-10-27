# The Loom Pattern: Youtube Master Island, chapter 55 (youtube-master, contest G333)

Chapters 1-54 run from melody brewing (G25) to the message shells (G323) and the lamp posts (G328). The fair is lit,
and every family wants a sash with its own pattern.

## Story

The weaver takes a long strip of coloured threads off the loom. Keeper Oriel asks the player to mark the first place
the family pattern starts, so the sash is cut there. A thread that starts a near-miss is FRAYED and earns no credit,
and if the pattern is not in the strip at all, every mark is FRAYED.

## Beats, mechanics and tests (`LoomPatternTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The strip | `seeded`: 1-30 threads over 2-3 colours, pattern of 1-4 | `seededLoomIsDeterministic` |
| The search | `starts()`: Knuth-Morris-Pratt with a failure table; equals brute force (30 seeds) | `startsMatchBruteForce` |
| Overlaps | `aaaa` holds `aa` at 0, 1 and 2; failure table of `abab` is 0,0,1,2 | `overlapsCount` |
| Frayed | `mark` at a near-miss or in a strip without the pattern is FRAYED, no credit | `frayedAndMissingEarnNoCredit` |
| Loom rules | `mark`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_loom_pattern` | colony `QuestProgress`: weave strip x1, mark first x1 (retries allowed), talk keeper_oriel | `questFrayedThenCleanThenKeeper` |

## Keeper Oriel's lines (`KeeperLoomLines`)

- Greeting: "A strip of 7 threads, and the family pattern is abab. Mark the first place the pattern starts, and we'll
  cut the sash there."
- Frayed: "At thread 0 the pattern breaks. It first starts at 3."
- Missing: "That pattern isn't in this strip at all. Weave another."
- Quest done: "Clean cut. The sash is yours to wear."
- After: "The sash is cut. Wear it to the fair."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A loom by the green, a long strip of coloured thread, a chalk mark, and the cut sash. Source-only here.
