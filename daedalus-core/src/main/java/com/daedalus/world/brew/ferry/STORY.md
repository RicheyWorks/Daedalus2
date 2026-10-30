# The Ferry Crossing: Youtube Master Island, chapter 27 (youtube-master, contest G223)

Chapters 1-26 run from melody brewing (G25) to the market lanes (G215) and the shell strings (G219). After a night at
the harbour inn the children must cross the outer isles to the next inn.

## Story

Ferries run between some of the isles, each charging its own fare in shells, and the purse is thin. Keeper Oriel asks
the player to get everyone from isle 0 to the inn on the last isle for as few shells as the tide allows. The player
sails leg by leg and docks at the inn. Docking at the cheapest fare docks well; paying more is dear and earns nothing.
If no ferries reach the inn, the crossing has no route and also earns nothing.

## Beats, mechanics and tests (`FerryCrossingTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The harbour | `seeded`: 4-7 isles, each leg runs with probability 1/2 at 1-9 shells | `seededHarbourIsDeterministic` |
| The cheapest way home | `cheapest()`: Dijkstra; equals brute force over every simple path from isle 0 (30 seeds) | `cheapestMatchesBruteForce` |
| The direct ferry is a trap | direct 0-3 costs 9, the 0-1-2-3 hop costs 3 | `directFerryIsNotAlwaysCheapest` |
| No ferry home | isle 3 cut off: `dock` is NO_ROUTE, no credit | `noRouteEarnsNoCredit` |
| Ferry rules | `sail` / `dock`: NO_FERRY, NOT_HOME, DUPLICATE, IGNORED | `guards` |
| Quest `q_ferry_crossing` | colony `QuestProgress`: sail leg x1, dock well x1 (DEAR can be retried with `restart`), talk keeper_oriel | `questDearThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperFerryLines`)

- Greeting: "Isle 0 to isle 3, and every ferry charges in shells. Get us home for as few as the tide allows."
- Sailing: "Isle 1 now, 1 shells paid."
- Dear: "Home, but 9 shells where 3 would have done. Try again tomorrow."
- No route: "No ferry runs that way home tonight. We stay put."
- Quest done: "Home, and not a shell wasted on the way. The purse thanks you."
- After: "The ferries are tied up. Sleep well."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A harbour map board with ferry routes chalked in fares, a small ferry that hops isle to isle, and the inn dock at the
far end. Source-only here.
