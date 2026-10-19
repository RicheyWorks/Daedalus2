# The Signal Fires: Youtube Master Island, chapter 17 (youtube-master, contest G174)

Chapters 1-16 run from melody brewing (G25) to the guest lofts (G149), the apprentices (G155) and the parting jars
(G167). The families are sailing, and nobody wants to wait a season for the next letter.

## Story

Keeper Oriel spreads a sea map on the table: home in the middle, the four far islands out at their ark distance,
and two bare sea stacks between. If every island keeps a signal fire, and every fire can see at least one other,
a call from anywhere reaches everyone. Each fire link burns wood by the mile, and wood is dear on a sky island. A
fire on a sea stack can stand between two islands and save wood, or it can be left dark. The player lights and
douses links until everyone is joined, then sends the signal round. If it went round on the least wood possible,
the islands answer warm; if not, the smoke says somebody overspent.

## Beats, mechanics and tests (`SignalFiresTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The sea map | `seaMap`: home at the centre, far islands at legs x 10 miles on their bearings (G97 routes), 2 seeded sea stacks; `Isle.woodTo` = distance rounded up | `seaMapPutsFarIslandsAtTheirArkDistance` |
| A stack in the middle saves wood | relays optional; equilateral triangle: 20 wood without, 18 with a centre stack, a far stack is left out | `aStackInTheMiddleSavesWood` |
| Least wood | `best()`: for each subset of stacks, Kruskal over islands plus those stacks, keep the cheapest (a small Steiner tree); equals brute force over link sets (12 seeds) | `leastWoodMatchesBruteForce` |
| Lighting rules | `light` / `douse` / `signal`: UNKNOWN_ISLE, SAME_ISLE, ALREADY_LIT, NOT_LIT, NOT_JOINED | `guards` |
| Quest `q_signal_fires` | colony `QuestProgress`: light link x4, signal warm x1 (SMOKY can be fixed), talk keeper_oriel | `questSmokyStarThenWarmTreeThenKeeper` |

## Keeper Oriel's lines (`KeeperFireLines`)

- Greeting: "Fires on every island, so one can call the others. Each link burns wood by the mile. The sea stacks
  can hold a fire too, if it saves wood."
- Building: "2 links lit, 31 wood. Not every island can see a fire yet."
- Ready: "Everyone's joined. Send the signal round."
- Smoky: "It went round, but you burned 112 where 96 would do. Douse a link and think again."
- Quest done: "Every island answered, and the woodpile hardly noticed. Now nobody's ever more than a fire away."
- After: "The fires are banked every night. Anyone can call."

## Editor later (UNREAL-QUEUE)

A sea-map table in the keeper's house (isles as tokens, links as cords, a wood counter), beacon braziers on each
island and sea stack that light along chosen links, and a signal moment where the fires chain round. Source-only
here.
