# The Market Lanes: Youtube Master Island, chapter 25 (youtube-master, contest G215)

Chapters 1-24 run from melody brewing (G25) to the lantern parade (G209) and the rope market (G212). The rope is sold
and the fleet has a night at the harbour inn.

## Story

The inn is on the far side of the market, down a grid of lanes, and every square is busy with its own crowd. The
lanes run downhill, so the children can only go east or south. Keeper Oriel wants the little ones kept out of the
thick of it. The player walks them square by square (and can back up), then knocks at the inn. The fewest people
passed makes an easy walk; more is jostled.

## Beats, mechanics and tests (`MarketLanesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The market | `seeded`: 3-6 by 3-6 squares with a crowd of 0-9 each | `seededMarketIsDeterministic` |
| The quiet lanes | `least()`: min-path-sum DP from the inn back to the gate; equals brute force over every east/south path (30 seeds); walking `bestPath()` reaches the inn passing exactly that crowd | `leastMatchesBruteForceAndPathAchievesIt` |
| The quiet next step is a trap | the quieter first square leads into the 50s; the best goes south | `theGreedyQuietestNextStepIsNotAlwaysBest` |
| Already there | a one-square market: knock straight away | `aOneSquareMarketIsAlreadyThere` |
| Walking rules | `step` / `back` / `arrive`: BLOCKED, AT_GATE, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_market_lanes` | colony `QuestProgress`: step lane x3, arrive easy x1 (JOSTLED can be fixed by backing up), talk keeper_oriel | `questJostledThenEasyThenKeeper` |

## Keeper Oriel's lines (`KeeperLaneLines`)

- Greeting: "The inn's down there, past every stall in town. East or south only, and keep the little ones out of the
  thick of it."
- Walking: "10 people passed so far."
- Ready: "That's the inn door. Knock."
- Jostled: "We made it, but through 21 people where 5 would do. Back up and find the quiet lanes."
- Quest done: "Through the market and hardly an elbow. Well walked."
- After: "Supper's on at the inn."

## Editor later (UNREAL-QUEUE)

A sloping market grid of stalls with crowd density per square, the harbour gate at the top and the inn at the bottom,
and the children's walk traced through the lanes. Source-only here.
