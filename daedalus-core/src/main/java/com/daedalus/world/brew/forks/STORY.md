# The Stream Forks: Youtube Master Island, chapter 52 (youtube-master, contest G319)

Chapters 1-51 run from melody brewing (G25) to the twin oars (G312) and the hauling days (G316). The first thaw
sends melt streams racing down the hill, and the children want to race paper boats.

## Story

Melt streams fork and meet again between pools from the spring down to the sea. Water only runs downhill. Keeper
Oriel asks how many different ways a paper boat can float from the spring to the sea, so every child can take a
different way. The player follows the streams and names a count. The exact count is right; any other earns no
credit. Forks multiply the ways rather than add to them.

## Beats, mechanics and tests (`StreamForksTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hillside | `seeded`: 3-9 pools, downhill streams; uphill streams refused; some hills never reach the sea | `seededHillIsDeterministic` |
| The routes | `routes()`: path counting by DP over the downhill (topological) order; equals brute-force enumeration (30 seeds) | `routesMatchBruteForce` |
| Forks multiply | two forks in a row: 4 routes, not 2 + 2 or 8 streams | `forksMultiply` |
| Wrong count | any other number: `count` is WRONG, no credit | `wrongCountEarnsNoCredit` |
| Stream rules | `count`: DUPLICATE, IGNORED | `guards` |
| Quest `q_stream_forks` | colony `QuestProgress`: follow streams x1, count right x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperForkLines`)

- Greeting: "The melt streams fork and meet again across 7 pools down to the sea. The children want to race paper
  boats: how many different ways can a boat float from the spring to the sea?"
- Wrong: "8? Follow the streams again; where they fork, the ways add up."
- Quest done: "That many! Every child can take a different way."
- After: "Paper boats bob all the way down to the sea."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A hillside of melt pools joined by forking streams, paper boats that pick a fork at each pool, and the sea at the
bottom. Source-only here.
