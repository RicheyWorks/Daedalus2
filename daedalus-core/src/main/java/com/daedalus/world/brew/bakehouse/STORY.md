# The Bakehouse: Youtube Master Island, chapter 35 (youtube-master, contest G248)

Chapters 1-34 run from melody brewing (G25) to the lighthouse relay (G242) and the island post (G245). The letters
are out, and the whole island is coming for the harvest bread.

## Story

The bakehouse has one kneading table and one oven. Every loaf is kneaded first, then baked, and the loaves go through
both in the same order. Keeper Oriel asks the player to queue the loaves so the last one is out of the oven as soon
as possible. The soonest finish bakes well; a later one is late and earns nothing, and the oven will not fire until
every loaf is queued.

## Beats, mechanics and tests (`BakehouseTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The batch | `seeded`: 3-7 loaves, 1-9 hours to knead and to bake | `seededBatchIsDeterministic` |
| The soonest finish | `soonest()`: Johnson's rule for the two-stage flow shop; equals brute force over every loaf order (30 seeds) | `soonestMatchesBruteForce` |
| Long bakes go first | loaf 0 knead 5 bake 1, loaf 1 knead 1 bake 5: order 1,0 finishes at 7, order 0,1 at 11 | `quickKneadsGoFirst` |
| Not all queued | `bake` is UNFINISHED; a late order is LATE, no credit | `lateEarnsNoCredit` |
| Queue rules | `queue`: ALREADY, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_bakehouse` | colony `QuestProgress`: queue loaf x1, bake well x1 (LATE can be re-planned with `restart`), talk keeper_oriel | `questLateThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperBakeLines`)

- Greeting: "2 harvest loaves. One kneading table, one oven, and every loaf is kneaded before it bakes. Choose the
  order that has them all out soonest."
- Queued: "1 of 2 loaves in the queue."
- Late: "All baked by hour 11, but hour 7 was possible. The feast is waiting."
- Quest done: "Every loaf out of the oven at the first possible hour. Smell that."
- After: "The oven is cooling. Tear off a crust."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A bakehouse with a kneading table, a stone oven, a loaf rack and a chalk queue board. Source-only here.
