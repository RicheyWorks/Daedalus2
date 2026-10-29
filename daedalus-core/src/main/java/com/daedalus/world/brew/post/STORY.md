# The Island Post: Youtube Master Island, chapter 34 (youtube-master, contest G245)

Chapters 1-33 run from melody brewing (G25) to the harvest feasts (G238) and the lighthouse relay (G242). The far isle
saw the signal, and now the harvest letters must go out by post boat.

## Story

The post boat leaves isle 0 with letters for every isle. It must call at each one once and row home, and every league
is rowed by hand. Keeper Oriel asks the player to plan the round. The shortest round home comes home well; a longer
one is long, and rowing home with isles still waiting is missed. Neither earns credit.

## Beats, mechanics and tests (`IslandPostTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The sea | `seeded`: 4-7 isles, 1-9 leagues apart | `seededSeaIsDeterministic` |
| The shortest round | `shortest()`: Held-Karp DP over subsets; equals brute force over every visiting order (30 seeds) | `shortestMatchesBruteForce` |
| Nearest-first is a trap | a square of isles where crossing to the diagonal isle first forces a 9-league row (12), the best round is 4 | `nearestFirstIsNotAlwaysShortest` |
| Missed isles | rowing home early: `home` is MISSED, no credit | `missedIslesEarnNoCredit` |
| Round rules | `call` / `home`: ALREADY, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_island_post` | colony `QuestProgress`: call isle x1, home well x1 (LONG can be retried with `restart`), talk keeper_oriel | `questLongThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperPostLines`)

- Greeting: "Harvest letters for 4 isles. Call at every one once and bring the boat home to isle 0 by the shortest
  round."
- Rowing: "2 isles called at, 1 leagues rowed."
- Missed: "Home already? 2 isles still wait for their letters."
- Long: "Every letter delivered, but 12 leagues where 4 would do. My arms ache."
- Quest done: "Every isle has its letters, and not a stroke wasted. Fine rowing."
- After: "The post bag is empty. Rest your oars."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A post boat with a letter bag, small post boxes on each isle's jetty, and a round chalked on a sea chart.
Source-only here.
