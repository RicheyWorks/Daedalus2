# The Causeway Wade: Youtube Master Island, chapter 98 (youtube-master, contest G479)

Chapters 1-97 run from melody brewing (G25) to the flood planks (G476) and the stage bookings (G478). At low tide a
causeway of stones links the main island to the bird islet.

## Story

The causeway is a grid of dry stones and cold shallows. Keeper Oriel walks from the near corner to the far corner,
north, south, east or west, and minds only the wading: a dry stone costs nothing, a shallow costs one wet step. Keeper
Oriel asks for the fewest wet steps. Walking the straight route, along the top and down the far side, is the trap.
A WRONG count earns no credit, and an all-DRY causeway leaves nothing to count.

## Beats, mechanics and tests (`CausewayWadeTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The causeway | `seeded`: 2-3 rows, 2-4 columns, about a third shallows | `seededIsDeterministic` |
| Fewest wet steps | `wades()`: 0-1 BFS with a deque (dry steps pushed to the front, wet ones to the back); equals brute force over every simple path (30 seeds), and the straight route never beats it | `answerMatchesBruteForce` |
| The straight route is a trap | rows .~~ .~~ ~..: 1 wet step, straight route 3 | `trap` |
| Wrong, dry | `count` WRONG, MALFORMED, DRY (no shallows), no credit | `wrongAndSpecialEarnNoCredit` |
| Causeway rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_causeway_wade` | colony `QuestProgress`: read causeway x1, count wades x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperCausewayWade`)

- Greeting: "The causeway reads [.~~, .~~, ~..], with . for dry stones and ~ for shallows. Corner to corner, what is
  the fewest wet steps?"
- Wrong: "Not 3. The straight route isn't the driest."
- Dry: "Every stone is dry today. No wading at all."
- Quest done: "One wet step! My socks are grateful."
- After: "The tide comes back and the causeway sleeps."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A low-tide stone causeway with shallow pools between stones, leading to a small bird islet. Source-only here.
