# The Mirror Chant: Youtube Master Island, chapter 69 (youtube-master, contest G395)

Chapters 1-68 run from melody brewing (G25) to the village vote (G387) and the tide gauge (G390). The new well is
built, and the village blesses it with a chant.

## Story

The chant is a line of syllables. Its mirror verse is the longest stretch that sings the same backwards. Keeper Oriel
asks the player to mark where it starts and ends. Short odd mirrors are easy to spot, but the even ones can be
longer; a SHORT mirror or a BROKEN stretch earns no credit.

## Beats, mechanics and tests (`MirrorChantTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The chant | `seeded`: 1-20 syllables over 2-3 sounds | `seededChantIsDeterministic` |
| The mirror verse | `longest()` and `verse()` by Manacher's algorithm; equals brute force over every stretch (30 seeds) | `longestMatchesBruteForce` |
| Even mirrors count | "abacddca": "aba" is 3, "acddca" is 6 | `evenMirrorsCount` |
| Broken | `mark` a stretch that doesn't mirror is BROKEN, no credit | `brokenEarnsNoCredit` |
| Circle rules | `mark`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_mirror_chant` | colony `QuestProgress`: hear chant x1, mark mirror x1 (retries allowed), talk keeper_oriel | `questShortThenMirrorThenKeeper` |

## Keeper Oriel's lines (`KeeperChantLines`)

- Greeting: "The chant is abacddca. The mirror verse is the longest stretch that sings the same backwards. Mark where
  it starts and ends."
- Short: "That mirrors, but only 3 long. One is 6."
- Broken: "acdd doesn't sing the same backwards."
- Quest done: "The mirror verse! Sing it both ways."
- After: "The circle sings the mirror verse."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A chant circle around the new well, syllable stones in a line, and singers facing each other. Source-only here.
