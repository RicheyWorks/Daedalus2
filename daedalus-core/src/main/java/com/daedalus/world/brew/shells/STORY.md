# The Shell Strings: Youtube Master Island, chapter 26 (youtube-master, contest G219)

Chapters 1-25 run from melody brewing (G25) to the rope market (G212) and the market lanes (G215). The children are
at the harbour inn for the night.

## Story

By the inn fire two children want matching shell strings to remember the voyage by. Each has a string of shells
(cowrie, whelk, scallop, periwinkle) threaded in the order they were found. Keeper Oriel says nobody re-threads: shells
can come off, but none can change place. The player takes shells off either string (or threads one back), then holds
them up together. Matching strings as long as they can be match well; matching but shorter is short.

## Beats, mechanics and tests (`ShellStringsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Two strings | `seeded`: two strings of 4-10 shells from c, w, s, p | `seededStringsAreDeterministic` |
| The longest match | `longest()`: longest common subsequence DP; equals brute force over every subsequence of the left string (30 seeds); `bestMatch()` walks it back and fits both | `longestMatchesBruteForce` |
| The first shell is a trap | "pcws" vs "cwsp": keeping the first p keeps 1 shell, dropping it keeps "cws" | `matchingTheFirstShellIsNotAlwaysBest` |
| Nothing in common | "cc" vs "ww": two empty strings are the best match | `noSharedShellsMatchEmpty` |
| Threading rules | `take` / `putBack` / `compare`: NOT_THERE, ALREADY_OFF, DIFFERENT, DUPLICATE, IGNORED | `guards` |
| Quest `q_shell_strings` | colony `QuestProgress`: take shell x3, compare well x1 (SHORT can be fixed by threading back), talk keeper_oriel | `questShortThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperShellLines`)

- Greeting: ""pcws" and "cwsp". Take shells off till they match, but don't reorder a single one, and keep them as
  long as you can."
- Threading: ""pws" and "cwsp" so far."
- Ready: "They match. Hold them up together."
- Short: "They match, but 1 shells long where 3 could be. Put some back."
- Quest done: "Two strings, the same shells in the same order, and nothing wasted. Keep them safe."
- After: "Off to bed, both of you, shells and all."

## Editor later (UNREAL-QUEUE)

Two shell strings on a table by the inn fire, shells that lift off and thread back in place, and the strings held up
side by side to compare. Source-only here.
