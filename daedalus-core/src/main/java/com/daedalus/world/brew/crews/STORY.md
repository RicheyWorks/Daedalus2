# The Fishing Crews: Youtube Master Island, chapter 40 (youtube-master, contest G269)

Chapters 1-39 run from melody brewing (G25) to the sea wall (G262) and the tide pools (G266). The winter rain has
passed and the shoals are running, so every boat must go out.

## Story

The quay has as many crews as boats, and each crew rows each boat in its own number of hours. Keeper Oriel wants one
crew on every boat and the fewest hours on the oars in all. The player asks the crews their hours and posts a rota.
The cheapest rota is right; a costlier one earns no credit, and a rota that sends one crew to two boats is a clash and
earns none.

## Beats, mechanics and tests (`FishingCrewsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The quay | `seeded`: 2-7 boats, 1-20 hours each | `seededHarbourIsDeterministic` |
| The best rota | `fewest()`: minimum-cost assignment by DP over subsets of crews; equals brute force over every permutation (30 seeds) | `fewestMatchesBruteForce` |
| Greedy is a trap | taking the quickest crew for boat 0 costs 13; the best rota costs 8 | `greedyIsNotBest` |
| Clash | one crew on two boats: `rota` is CLASH, no credit | `clashEarnsNoCredit` |
| Quay rules | `rota`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_fishing_crews` | colony `QuestProgress`: ask crews x1, rota well x1 (COSTLY can be redone), talk keeper_oriel | `questCostlyThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperCrewLines`)

- Greeting: "3 boats and 3 crews, and every crew rows each boat at its own pace. One crew to a boat, and the fewest
  hours on the oars in all."
- Clash: "One crew can't row two boats. Somebody is left on the quay."
- Costly: "That rota takes 13 hours. It can be done in 8."
- Quest done: "The fewest hours on the oars. The crews will thank you."
- After: "The boats are out. Watch for the nets coming in."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A quay with a rota board, crews waiting by their boats, and boats that push off as the rota is posted. Source-only
here.
