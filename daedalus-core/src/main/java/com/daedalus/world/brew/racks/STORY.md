# The Smokehouse Racks: Youtube Master Island, chapter 41 (youtube-master, contest G272)

Chapters 1-40 run from melody brewing (G25) to the tide pools (G266) and the fishing crews (G269). The boats come
home full, and the catch must be smoked before it spoils.

## Story

The catch is a pile of fish sides of different weights. Every smokehouse rack holds the same load, and the winter fire
is small, so Keeper Oriel wants the catch on as few racks as possible. The player weighs the catch and hangs it. The
fewest racks is right; more racks are wasteful, and an overloaded rack would snap into the fire. Neither earns credit.

## Beats, mechanics and tests (`SmokehouseRacksTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The catch | `seeded`: 2-8 sides, 1-9 each, racks hold 10 | `seededCatchIsDeterministic` |
| The fewest racks | `fewest()`: exact bin packing by DP over subsets of sides; equals brute force over every placement (30 seeds) | `fewestMatchesBruteForce` |
| First fit is a trap | 5,4,3,3,3,2 in order takes 3 racks; 5+3+2 and 4+3+3 take 2 | `firstFitInOrderIsNotBest` |
| Overload | a rack past its load: `hang` is OVERLOAD, no credit | `overloadEarnsNoCredit` |
| Smokehouse rules | `hang`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_smokehouse_racks` | colony `QuestProgress`: weigh catch x1, hang well x1 (WASTEFUL can be rehung), talk keeper_oriel | `questWastefulThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperRackLines`)

- Greeting: "6 sides of fish, and every rack holds 10. The fire is small this winter: hang the catch on as few racks
  as you can."
- Overload: "Rack 0 is holding too much. It will snap into the fire."
- Wasteful: "That is 3 racks. The catch fits on 2."
- Quest done: "As few racks as the catch allows. The smoke will reach every side."
- After: "The fish are smoking. Smell that."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A smokehouse with rows of racks, fish sides that hang where the player drops them, and a rack that bows when
overloaded. Source-only here.
