# The Echo Cave: Youtube Master Island, chapter 30 (youtube-master, contest G232)

Chapters 1-29 run from melody brewing (G25) to the island flags (G226) and the fair winds (G229). Waiting for the wind,
the children explore a sea cave on the last isle.

## Story

The cave wall is carved with a row of note marks (do, re, mi, fa, so). Keeper Oriel says the cave only sings back a
chant that sounds the same backwards. The player may skip marks but must sing the rest in wall order. The longest such
chant echoes well; a shorter echo is short, and a chant that does not read the same backwards gets no echo. Neither
earns credit.

## Beats, mechanics and tests (`EchoCaveTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The wall | `seeded`: 4-12 marks from d, r, m, f, s | `seededWallIsDeterministic` |
| The longest echo | `longest()`: longest palindromic subsequence by interval DP; equals brute force over every subsequence (30 seeds); `bestChant()` is a palindrome on the wall | `longestMatchesBruteForce` |
| Skipping pays | "drmrsd": skipping s gives "drmrd" (5) | `skippingAMarkCanPay` |
| No echo | a chant that is not a palindrome: `sing` is NO_ECHO, no credit | `noEchoEarnsNoCredit` |
| Wall rules | `sing`: NOT_ON_WALL, DUPLICATE, IGNORED | `guards` |
| Quest `q_echo_cave` | colony `QuestProgress`: read wall x1, sing well x1 (SHORT can be retried), talk keeper_oriel | `questShortThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperEchoLines`)

- Greeting: "The marks on the wall read "drmrsd". Sing them in order, skip what you like, but the cave only answers a
  chant that sounds the same backwards."
- No echo: ""drm" does not come back the same. The cave stays silent."
- Short: "It echoes, but 3 notes where 5 could. Sing more of the wall."
- Quest done: "The whole cave sang it back. That is the longest echo the wall holds."
- After: "Hush now, the cave is still ringing."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A sea cave mouth with a carved mark wall, marks that glow as they are sung, and an echo that plays the chant back.
Source-only here.
