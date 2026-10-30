# The Fair Winds: Youtube Master Island, chapter 29 (youtube-master, contest G229)

Chapters 1-28 run from melody brewing (G25) to the ferry crossing (G223) and the island flags (G226). With the flags
flying, the crew readies the boat for the long sail home.

## Story

The wind almanac scores every day of the season: fair days above zero, foul days below. The crew can only sail one
unbroken run of days, at least one, and wants the most wind out of it. Keeper Oriel reads the almanac aloud and asks
the player to choose the run. The best total sails well; any weaker run is weak and earns nothing.

## Beats, mechanics and tests (`FairWindsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The almanac | `seeded`: 5-14 days scoring -6 to 6 | `seededAlmanacIsDeterministic` |
| The best run | `best()`: Kadane's scan; equals brute force over every run (30 seeds); `bestRun()` sums to it | `bestMatchesBruteForce` |
| Sailing through a foul day | 4, -1, 5: the whole run (8) beats either fair day alone | `crossingAFoulDayCanPay` |
| A season of storms | every day foul: the least foul single day is best | `allFoulPicksTheMildestDay` |
| Weak run | a weaker run: `sail` is WEAK, no credit; NOT_THERE, DUPLICATE, IGNORED guards | `weakRunEarnsNoCredit` |
| Quest `q_fair_winds` | colony `QuestProgress`: read almanac x1, sail well x1, talk keeper_oriel | `questWeakThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperWindLines`)

- Greeting: "3 days in the almanac, fair winds and foul. Pick one unbroken run to sail, and make the most of it."
- Weak: "Days 0 to 0 give 4, but the best run gives 8. Read it again."
- Quest done: "The best winds of the season, and we caught every one. Hoist the sail."
- After: "The almanac is shut. The wind will do the rest."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A wind almanac book on a lectern with day pages, a weathervane, and a sail that fills for the chosen run.
Source-only here.
