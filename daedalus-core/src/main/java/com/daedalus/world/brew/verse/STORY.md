# The Lost Verse: Youtube Master Island, chapter 22 (youtube-master, contest G204)

Chapters 1-21 run from melody brewing (G25) to the two boats (G194) and the water casks (G199). The boats are beached
by the spring for a second night.

## Story

Round the fire the Song School children (G116) sing the landing chant, but a verse has drifted: a letter swapped
here, one dropped there. The true words are carved on the stern board. The player mends the sung verse one letter at
a time (swap a letter, add one, drop one), then has the children sing it back. Matching the carving with the fewest
changes rings true; matching it with more is rough, and the player can start over.

## Beats, mechanics and tests (`VerseMendTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The drift | `seeded`: one true word with 1-3 random letter edits | `seededDriftIsDeterministic` |
| The lightest mending | `fewest()`: Levenshtein DP; equals plain recursion with no table (30 seeds, short verses); `bestScript()` walks the table back and mends the verse | `fewestMatchesRecursionAndScriptMends` |
| One drop beats many swaps | "ttide" to "tide" is a single drop | `oneDropBeatsManySwaps` |
| A forgotten verse | an empty verse is all adds | `anEmptyVerseIsAllAdds` |
| Mending rules | `change` / `startOver` / `ring`: BAD_EDIT, OFF, DUPLICATE, IGNORED | `guards` |
| Quest `q_lost_verse` | colony `QuestProgress`: change letter x3, ring true x1 (ROUGH can be fixed by starting over), talk keeper_oriel | `questRoughThenTrueThenKeeper` |

## Keeper Oriel's lines (`KeeperVerseLines`)

- Greeting: "They're singing "wern". The stern says "wren". Mend it gently; every change is one more thing for small
  heads to unlearn."
- Mending: ""wrn" now, after 1 changes."
- Ready: "That's the carving, letter for letter. Sing it."
- Rough: "Right words, but 4 changes where 2 would do. Start over and go lighter."
- Quest done: "That's how the verse went when the boat was built. Well mended."
- After: "They'll sing it right on every shore now."

## Editor later (UNREAL-QUEUE)

A beach fire with the children in a ring, the carved stern board lit by the fire, and the sung verse floating as
letter tiles that can be swapped, added or dropped. Source-only here.
