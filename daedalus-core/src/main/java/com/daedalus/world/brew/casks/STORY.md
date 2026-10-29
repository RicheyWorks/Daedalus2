# The Water Casks: Youtube Master Island, chapter 21 (youtube-master, contest G199)

Chapters 1-20 run from melody brewing (G25) to the night watch (G186) and the two boats (G194). The boats are
across the shallows and beached by a spring.

## Story

The tank in each boat takes an exact measure of fresh water. The casks at the spring come in a few fixed sizes, and
each one is a climb up the hill and back. The player pours casks into the tank (or bails one back out), then seals
it. Right to the line with the fewest casks is neat; right to the line with more is wasteful. If no mix of the casks
can ever make the measure, Keeper Oriel calls it off with no credit.

## Beats, mechanics and tests (`WaterCasksTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The spring | `seeded`: 2-4 cask sizes from 2-11, a measure of 10-40 | `seededSpringIsDeterministic` |
| The fewest climbs | `fewest()`: unbounded coin-change DP; equals brute force over every count of every size (40 seeds); `bestPour()` walks it back | `fewestMatchesBruteForce` |
| Biggest first isn't enough | 8 from {1,4,5}: biggest first takes 4 casks (5+1+1+1), the fewest is 4+4 | `biggestCaskFirstIsNotAlwaysFewest` |
| A measure nobody can make | 9 from {4,6}: `seal` returns NO_FILL, no quest credit | `anUnreachableMeasureIsNoFillWithNoCredit` |
| Tank rules | `pour` / `empty` / `seal`: UNKNOWN, NOT_POURED, SHORT, OVER, DUPLICATE, IGNORED | `guards` |
| Quest `q_water_casks` | colony `QuestProgress`: pour cask x4, seal neat x1 (WASTEFUL can be fixed), talk keeper_oriel | `questWastefulThenNeatThenKeeper` |

## Keeper Oriel's lines (`KeeperCaskLines`)

- Greeting: "The tank takes 8 measures, no more, no less. Every cask we haul is a trip up the hill, so use as few as
  you can."
- Filling: "5 of 8 in the tank."
- Ready: "Right to the line. Seal it."
- Wasteful: "Full, but that was 4 casks where 2 would do. My knees noticed."
- No fill: "No mix of these casks makes 9. We'll top it up by hand at the next spring."
- Quest done: "Exact, and hardly a trip wasted. The spring thanks you."
- After: "The tank's sealed and sweet."

## Editor later (UNREAL-QUEUE)

A hillside spring with stacked casks of marked sizes, a tank with a measure line in the beached boat, and the water
level rising as casks are poured. Source-only here.
