# G157 The Birth-Night Lanterns (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/match/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

At the ark muster every sailor hangs a lantern on the night of the island year they were born. The
Odds Keeper asks the crowd: how many hands before two lanterns more likely than not hang on the same
night? Most guess well over a hundred. The answer is 23 (50.7%). Two lanterns within a night of each
other take only 14 (53.7%). Then thirty are mustered and the lanterns are lit; seven musters in ten
show a shared night.

| Story beat | Mechanic in code |
|---|---|
| Shared birth night | `BirthNightOdds.shareChance`: 1 - prod (d - i)/d, smallest even-chance crew 23 for d = 365 |
| Within a night or two (the year wraps) | `nearChance(n, k)`: 1 - prod over i = 1..n-1 of (d - nk - i)/d; 14 for k = 1, 11 for k = 2 |
| How many matches to expect | `expectedPairs`: C(n, 2)(2k + 1)/d |
| The muster itself | `CrewMuster`: seeded birth nights, closest circular gap, `simulate` with Wilson interval |
| Guess, muster, light the lanterns | `BirthNightQuest` (q_birth_nights) |

Checks: 23/14/11 are pinned as the smallest crews crossing 0.5 (one fewer stays below: 47.6%, 48.3%, 47.2%); the year wraps, so nights 365 and 1 are neighbours (`CrewMuster.of` test); `nearChance` equals full enumeration of every crew on a 12-night year (n 2..4, k 0..2);
seeded musters land within a Wilson interval of the exact 23-crew figure.

## Quest q_birth_nights

1. GUESSING: "A 365-night year. How many hands before two share a birth night, more likely than not? And within a night of each other?"
2. MUSTERED: "23 for a shared night (50.7%), 14 within a night (53.7%). Thirty mustered: two share a night / no shared night, closest G nights apart (71% for thirty). N of 2 nods." (a nod for each guess within 2)

No wagering.

## Editor / asset needs (later, not in this PR)

- Lantern wall with 365 hooks (or a ring), muster crowd, lantern lighting effect.
