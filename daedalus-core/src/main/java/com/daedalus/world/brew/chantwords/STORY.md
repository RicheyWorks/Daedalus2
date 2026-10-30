# The Chant Words: Youtube Master Island, chapter 99 (youtube-master, contest G481)

Chapters 1-98 run from melody brewing (G25) to the stage bookings (G478) and the causeway wade (G479). The festival
opens with the old chant, sung without breaks between words.

## Story

The chant is one long run of syllables. Keeper Oriel has a list of blessing words and asks how many times blessings
are sung in all, counting every place a word appears, even where words overlap or one sits inside another. Counting
only which words turn up is the trap. A WRONG count earns no credit, and a SILENT chant with no blessings in it
leaves nothing to count.

## Beats, mechanics and tests (`ChantWordsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The chant | `seeded`: 0-12 syllables from a-c, 1-3 distinct words of 1-3 syllables | `seededIsDeterministic` |
| Every blessing | `total()`: Aho-Corasick automaton (trie, breadth-first failure links, match counts summed along failure links), one pass over the chant; equals brute force checking every word at every position (30 seeds) | `answerMatchesBruteForce` |
| Which words is a trap | chant aaab, words a, aa, ab: 6 blessings, 3 words found | `trap` |
| Wrong, silent | `count` WRONG, MALFORMED, SILENT (no blessing in the chant), no credit | `wrongAndSpecialEarnNoCredit` |
| Chant rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_chant_words` | colony `QuestProgress`: read chant x1, count blessings x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperChantWords`)

- Greeting: "The chant runs aaab, and the blessing words are [a, aa, ab]. Counting every place one is sung, overlaps
  too, how many blessings are there?"
- Wrong: "Not 3. Count every time a blessing is sung, not just which ones."
- Silent: "No blessing is sung in this chant. Nothing to count."
- Quest done: "Every blessing counted! The festival is well begun."
- After: "The chant fades and the blessings stay."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A festival circle of singers around a fire, with the blessing words painted on hanging banners. Source-only here.
