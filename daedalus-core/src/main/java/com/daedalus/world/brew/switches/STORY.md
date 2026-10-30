# The Lantern Switches: Youtube Master Island, chapter 95 (youtube-master, contest G474)

Chapters 1-94 run from melody brewing (G25) to the beacon fence (G471) and the kin tree (G472). The harbour lanterns
send signals to the boats, one switch per lantern.

## Story

A row of harbour lanterns is lit in one pattern, and the boats need another. Each switch flips one lantern. Keeper
Oriel reads both patterns as binary numbers and asks for the fewest flips. Subtracting the two numbers is the trap:
0111 and 1000 are one apart as numbers but differ in every lantern. A WRONG count earns no credit, and patterns that
already MATCH need no flips.

## Beats, mechanics and tests (`LanternSwitchesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The row | `seeded`: 1-6 lanterns, two random patterns | `seededIsDeterministic` |
| Fewest flips | `flips()`: XOR of the patterns, then count set bits by clearing the lowest one each step (x &= x - 1); equals brute force by breadth-first search over single flips (30 seeds) | `answerMatchesBruteForce` |
| Subtracting is a trap | 4 lanterns, 0111 to 1000: 4 flips, numbers 1 apart | `trap` |
| Wrong, match | `count` WRONG, MALFORMED, MATCH (same pattern), no credit | `wrongAndSpecialEarnNoCredit` |
| Harbour rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_lantern_switches` | colony `QuestProgress`: read lanterns x1, count flips x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperLanternSwitches`)

- Greeting: "The harbour lanterns read 0111, and the boats need 1000. Each switch flips one lantern. What is the fewest
  flips?"
- Wrong: "Not 1. Count the lanterns that differ, not the gap between the numbers."
- Match: "The lanterns already show the signal. No flips needed."
- Quest done: "Fewest flips! The boats read us clearly."
- After: "On, off, on: the harbour speaks in light."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A harbour wall with a row of signal lanterns and a brass switch board beneath them. Source-only here.
