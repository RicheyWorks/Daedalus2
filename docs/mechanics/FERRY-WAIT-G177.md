# G177 The Sky-Ferry Wait (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/poisson/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

Sky ferries reach the dock at random, one every 20 minutes on average, with no timetable. The Odds
Keeper asks travellers how long they will wait if they walk down at a random time. Most say 10, half
a gap. The truth is 20: ferries don't remember when the last one left, and a traveller is more likely
to walk into a long gap than a short one, so the gap they land in averages 40 minutes. With a fixed
timetable the same 20-minute service would mean a 10-minute wait.

| Story beat | Mechanic in code |
|---|---|
| Ferries at random | `FerryClock`: Poisson counts (lambda t)^k e^(-lambda t)/k! |
| How long you wait | `waitBeyond(t)` = e^(-lambda t), `expectedWait` = mean gap (memoryless), `waitQuantile` |
| Why it feels slow | `landedGapMean` = 2 x mean gap (inspection paradox), `timetableWait` = half the gap |
| The dock itself | `FerryDay`: seeded ferry stream, traveller's wait and landed gap; `simulate` with Wilson interval on P(wait > t) |
| Guess, then wait | `FerryWaitQuest` (q_ferry_wait) |

Numbers (mean gap 20): average wait 20, landed gap 40, timetable wait 10, P(wait > 30) = e^(-1.5) = 22.3%, median wait 13.9.

## Quest q_ferry_wait

1. GUESSING: "A ferry every 20 minutes on average, but no timetable. Walk down any time: how long do you wait?"
2. BOARDED: "You waited W minutes in a G-minute gap. Average wait 20, not 10: you tend to land in the long gaps (they average 40). Over 30 minutes: 22%. Good guess. / Not my nod." (a nod for a guess within 3 of 20)

No wagering.

## Editor / asset needs (later, not in this PR)

- Dock clock, ferry arrival animation, traveller wait timer.
