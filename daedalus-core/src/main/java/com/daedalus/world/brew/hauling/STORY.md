# The Hauling Days: Youtube Master Island, chapter 51 (youtube-master, contest G316)

Chapters 1-50 run from melody brewing (G25) to the goat leaps (G306) and the twin oars (G312). The grain from the
mill (G254) must go up to the hill loft before the snow.

## Story

Grain sacks stand in a line by the mill and must be carted up the hill in that order over a set number of days. The
pony is old, so Keeper Oriel wants the heaviest day as light as it can be. The player counts the sacks and plans which
day each goes. A plan with the lightest possible heaviest day is right; a heavier plan earns no credit.

## Beats, mechanics and tests (`HaulingDaysTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The line | `seeded`: 1-9 sacks of 1-12, 1-4 days | `seededLineIsDeterministic` |
| The lightest heaviest day | `lightest()`: binary search on the day load with a greedy days-needed check; equals brute force over every split (30 seeds) | `lightestMatchesBruteForce` |
| Known lines | 7, 2, 5, 10, 8 over 2 days: 18; with spare days the biggest sack (10) decides | `knownLine` |
| Heavy | a plan above the lightest: `plan` is HEAVY, no credit | `heavyPlanEarnsNoCredit` |
| Hauling rules | `plan`: NOT_THERE (out of order or no such day), DUPLICATE, IGNORED | `guards` |
| Quest `q_hauling_days` | colony `QuestProgress`: count sacks x1, plan well x1 (HEAVY can be replanned), talk keeper_oriel | `questHeavyThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperHaulLines`)

- Greeting: "5 sacks in a line, and 2 days to cart them up the hill in that order. Plan it so the heaviest day is as
  light as it can be. The pony is old."
- Heavy: "One day carries 23. Split it better and no day needs more than 18."
- Quest done: "Even days. The pony will make it."
- After: "The grain is in the loft."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A line of grain sacks by the mill, a pony cart that climbs the hill once per day, and a loft that fills. Source-only
here.
