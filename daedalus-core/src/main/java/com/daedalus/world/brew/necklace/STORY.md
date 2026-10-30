# The Shell Necklace: Youtube Master Island, chapter 100 (youtube-master, contest G482)

Chapters 1-99 run from melody brewing (G25) to the causeway wade (G479) and the chant words (G481). For the hundredth
chapter, the island children string a long shell necklace for Keeper Oriel.

## Story

The necklace is one strand of shells in a row. Any unbroken run of shells can be cut out as a bracelet. Keeper Oriel
asks how many different bracelets could be cut. Counting every cut is the trap, since two cuts with the same shells in
the same order make the same bracelet. A WRONG count earns no credit, and a BARE string with no shells has nothing to
cut.

## Beats, mechanics and tests (`ShellNecklaceTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The necklace | `seeded`: 0-10 shells from a-c | `seededIsDeterministic` |
| Different bracelets | `distinct()`: suffix array by prefix doubling, Kasai's longest-common-prefix array, then n(n+1)/2 minus the LCP sum; equals brute force with a set of every substring (30 seeds) | `answerMatchesBruteForce` |
| Every cut is a trap | necklace aaa: 3 bracelets, 6 cuts | `trap` |
| Wrong, bare | `count` WRONG, MALFORMED, BARE (no shells), no credit | `wrongAndSpecialEarnNoCredit` |
| Craft rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_shell_necklace` | colony `QuestProgress`: read necklace x1, count bracelets x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperShellNecklace`)

- Greeting: "The children strung the shells aaa. Any unbroken run can be cut as a bracelet. How many different
  bracelets could there be?"
- Wrong: "Not 6. Two cuts with the same shells in the same order are the same bracelet."
- Bare: "There are no shells on this string yet. Nothing to cut."
- Quest done: "Every bracelet counted! A hundred tales, and still you count true."
- After: "The necklace shines, and every bracelet in it."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A long shell necklace laid across a driftwood table, with small shell bracelets beside it. Source-only here.
