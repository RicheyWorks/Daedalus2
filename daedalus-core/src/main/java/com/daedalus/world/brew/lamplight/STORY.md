# The Lamplighter's Round: Youtube Master Island, chapter 74 (youtube-master, contest G410)

Chapters 1-73 run from melody brewing (G25) to the drum lines (G404) and the twin braids (G407). Night comes early
in the cold months, and the lamp posts round the village ring need lighting.

## Story

The lamp posts stand in a ring. At each post a villager leaves a little oil for the lamplighter's can, and each walk
to the next post burns some. Keeper Oriel asks for the first post where he can start and walk the whole ring without
his can running dry. Starting at the post with the most oil is a trap. A DRY start, a LATER post when an earlier one
works, or a bad pick earns no credit, and if the ring burns more oil than it holds it is SHORT and no start will do.

## Beats, mechanics and tests (`LamplighterRoundTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The ring | `seeded`: 1-7 posts, oil 0-6, burn 0-6 | `seededRingIsDeterministic` |
| First good post | `start()`: one-pass circular greedy (restart after every deficit); equals brute force walking from every post (30 seeds) | `startMatchesBruteForce` |
| Most oil is a trap | post 4 holds 5 oil but runs dry; only post 3 works | `mostOilFirstIsATrap` |
| Dry, later, short | `name` DRY, MALFORMED, LATER, SHORT (ring burns more than it holds), no credit | `dryLaterAndShortEarnNoCredit` |
| Ring rules | `name`: IGNORED, DUPLICATE | `guards` |
| Quest `q_lamplighter_round` | colony `QuestProgress`: walk ring x1, start post x1 (retries allowed), talk keeper_oriel | `questDryThenFirstThenKeeper` |

## Keeper Oriel's lines (`KeeperLamplighter`)

- Greeting: "5 lamp posts in a ring, each with a little oil left out. Tell me the first post where the lamplighter
  can start and walk the whole ring without his can running dry."
- Later: "Post 2 works, but post 0 works too and comes first."
- Dry: "From post 4 his can runs dry before the ring is done."
- Short: "The ring burns more oil than the posts hold. No start will do."
- Quest done: "Post 3 it is. Every lamp lit, can never empty!"
- After: "The lamps glow all the way round the ring."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A ring of lamp posts with small oil jars at their feet, a lamplighter with a can and a pole. Source-only here.
