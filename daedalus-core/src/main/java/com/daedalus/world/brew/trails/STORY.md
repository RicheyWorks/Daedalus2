# The Hill Trails: Youtube Master Island, chapter 56 (youtube-master, contest G338)

Chapters 1-55 run from melody brewing (G25) to the lamp posts (G328) and the loom pattern (G333). After the fair, a
child up the hill is sick.

## Story

Huts dot the hill, joined by two-way trails of different lengths. The healer must walk from the first hut to the last
tonight, and Keeper Oriel asks the player to show the shortest way. The straight trail is not always the short one. A
LONG walk or a BROKEN route (a step with no trail, or one that starts or ends at the wrong hut) earns no credit.

## Beats, mechanics and tests (`HillTrailsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hill | `seeded`: 2-6 huts, 0-9 trails of length 1-9 | `seededHillIsDeterministic` |
| Every short way | `dist(a, b)`: Floyd-Warshall all pairs; equals brute force over simple paths (30 seeds, every pair) | `allPairsMatchBruteForce` |
| Straight is a trap | trail 0-3 is 10, the walk 0-1-2-3 is 6; unjoined huts are `NONE` | `straightTrailIsNotShortest` |
| Long or broken | `walk` LONG or BROKEN, no credit | `longAndBrokenEarnNoCredit` |
| Trail rules | `walk`: BROKEN at the wrong start, DUPLICATE, IGNORED | `guards` |
| Quest `q_hill_trails` | colony `QuestProgress`: survey trails x1, walk shortest x1 (retries allowed), talk keeper_oriel | `questLongThenShortestThenKeeper` |

## Keeper Oriel's lines (`KeeperTrailLines`)

- Greeting: "4 huts on the hill and trails between them. The healer must walk from hut 0 to hut 3 tonight. Show me the
  shortest way."
- Long: "That walk is 10. There is one of 6."
- Broken: "There's no trail along that way."
- Quest done: "That's the way. The healer is off with a lantern."
- After: "The healer knows every short way now."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Huts on a hillside, dirt trails with marker stones, and the healer's lantern moving along the walk. Source-only here.
