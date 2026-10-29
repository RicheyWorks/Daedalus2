# The Twin Oars: Youtube Master Island, chapter 50 (youtube-master, contest G312)

Chapters 1-49 run from melody brewing (G25) to the two buckets (G301) and the goat leaps (G306). The new boat from
the boatyard (G275) is afloat but has no oars.

## Story

A pile of oars of different lengths lies in the boatyard. The boat's oarlocks take a pair whose lengths together reach
the span without passing it, or the blades clash in the middle. Keeper Oriel asks for the pair that comes closest.
The player sorts the pile and picks two oars. The closest pair is right; a shorter pair earns no credit, and a pair
past the span earns none.

## Beats, mechanics and tests (`TwinOarsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The pile | `seeded`: 2-12 oars of 1-20, a span of 5-40; some piles have no fitting pair | `seededPileIsDeterministic` |
| The best pair | `best()`: two pointers on the sorted lengths; equals brute force over every pair (30 seeds) | `bestMatchesBruteForce` |
| The longest pair is a trap | 9, 4, 7, 2, 11 for 15: 11 + 9 = 20 is over; 4 + 11 = 15 | `longestPairIsNotBest` |
| Over | a pair past the span: `pick` is OVER, no credit | `overSpanEarnsNoCredit` |
| Pile rules | `pick`: NOT_THERE, SHORT, DUPLICATE, IGNORED | `guards` |
| Quest `q_twin_oars` | colony `QuestProgress`: sort pile x1, pick well x1 (SHORT can be redone), talk keeper_oriel | `questShortThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperOarLines`)

- Greeting: "5 oars in the pile. The new boat's oarlocks span 15: pick two oars that together come as close to that
  as they can without passing it."
- Over: "Together that's 20. Past the span: they'd clash in the middle."
- Short: "That's 13. A better pair reaches 15."
- Quest done: "A fine pair. She'll row straight."
- After: "The oars are in the locks."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

An oar pile that sorts itself by length, a measuring board, and the new boat with oarlocks. Source-only here.
