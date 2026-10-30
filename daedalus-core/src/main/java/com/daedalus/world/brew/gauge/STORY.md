# The Tide Gauge: Youtube Master Island, chapter 68 (youtube-master, contest G390)

Chapters 1-67 run from melody brewing (G25) to the pebble line (G383) and the village vote (G387). The vote chose a
well on the far point, and the boat must carry the stones there over the reef.

## Story

A tide gauge on the jetty logs the water level each hour. The boat goes out at one hour and comes back at another.
Keeper Oriel asks how low the water gets while it is out, so the keel clears the reef. The levels at the ends of the
trip are a trap, and so is a low that comes after the boat is home; a WRONG low earns no credit.

## Beats, mechanics and tests (`TideGaugeTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The log | `seeded`: 1-20 hours of levels -5..9 and a trip inside it | `seededLogIsDeterministic` |
| The low | `low(a, b)`: sparse table range minimum in constant time; equals a brute-force scan for every range (30 seeds) | `everyRangeMatchesBruteForce` |
| Ends are a trap | levels 6, 4, 5, 1, 3, 7, 0 and trip 1-5: ends 4 and 7, low 1; the 0 is after the trip | `endsAreATrap` |
| Wrong | `name` a wrong low is WRONG, no credit | `wrongEarnsNoCredit` |
| Gauge rules | `name`: DUPLICATE, IGNORED | `guards` |
| Quest `q_tide_gauge` | colony `QuestProgress`: read gauge x1, name low x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperGaugeLines`)

- Greeting: "The gauge logged 7 hours of water. The boat goes out at hour 1 and back at hour 5. How low does the water
  get while it's out?"
- Wrong: "You said 0. The water drops to 1."
- Quest done: "That's the low. The keel will clear it."
- After: "The boat came home over the low water safely."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A marked tide post on the jetty, a log slate with hourly chalk marks, and a stone boat over the reef. Source-only here.
