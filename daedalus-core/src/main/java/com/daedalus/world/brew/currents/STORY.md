# The Sea Currents: Youtube Master Island, chapter 59 (youtube-master, contest G351)

Chapters 1-58 run from melody brewing (G25) to the bell tower (G342) and the beach mats (G348). The dried fish must go
by boat to the far cove.

## Story

One-way currents run between the coves. Rowing against the sea costs effort, but some currents carry the boat and
give effort back. Keeper Oriel asks the player for the sail from the first cove to the last with the least effort. The
straight sail is not always cheapest. A COSTLY or BROKEN route earns no credit, and a circle of currents that keeps
giving effort back is a WHIRLPOOL nobody sails.

## Beats, mechanics and tests (`SeaCurrentsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The sea | `seeded`: 2-6 coves, 0-10 forward currents of effort -4..8 | `seededSeaIsDeterministic` |
| Least effort | `cost(c)`: Bellman-Ford with negative edges; equals brute force over simple routes (30 seeds, every cove) | `costsMatchBruteForce` |
| Straight is a trap | straight 0-3 costs 4; 0-1-2-3 with a helping current costs 1 | `helpingCurrentBeatsStraight` |
| Costly, broken, whirlpool | `sail` COSTLY, BROKEN or WHIRLPOOL (negative cycle found by an extra relax pass), no credit | `costlyBrokenAndWhirlpoolEarnNoCredit` |
| Sea rules | `sail`: BROKEN at the wrong start, DUPLICATE, IGNORED | `guards` |
| Quest `q_sea_currents` | colony `QuestProgress`: chart currents x1, sail cheapest x1 (retries allowed), talk keeper_oriel | `questCostlyThenCheapestThenKeeper` |

## Keeper Oriel's lines (`KeeperCurrentLines`)

- Greeting: "4 coves. Rowing costs effort, but some currents carry you and give it back. Sail from cove 0 to cove 3 for
  the least effort."
- Costly: "That sail costs 4. One costs 1."
- Broken: "No current runs that way."
- Whirlpool: "Those currents circle forever. Nobody sails into a whirlpool."
- Quest done: "Least effort. The rowers will thank you."
- After: "The boat rides the currents home."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A harbour chart with current arrows between coves, a rowing boat, and a whirlpool marker. Source-only here.
