# The Keepsake Chests: Youtube Master Island, chapter 18 (youtube-master, contest G181)

Chapters 1-17 run from melody brewing (G25) to the parting jars (G167) and the signal fires (G174). The fires are
lit; the boats are at the jetty.

## Story

Keeper Oriel sets one sea chest on the jetty for each family bound for a far island. The boats are small, and each
chest has a weight the boat will take and not a pound more. Every house has more keepsakes than any chest can hold:
the quilt, the kettle, the fiddle, the seed tin, a jar of home sand. The player packs and unpacks, then closes the
lid. If the chest holds the most memory that could fit, it closes warm; if a lighter choice would have carried more
of home, it closes heavy-hearted and can be opened again.

## Beats, mechanics and tests (`KeepsakeChestsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| One chest a family | `seeded`: a chest per G97 far-island family, 6-8 seeded keepsakes (weight, memory), limit 35-60% of the house | `oneChestPerFarIslandFamilyAndDeterministic` |
| The heaviest love isn't always best | quilt (6, 30) loses to fiddle + letters (5+5, 40) in a 10 chest | `greedyByValueIsNotEnough` |
| The most memory that fits | `best()`: exact 0/1 knapsack DP with walk-back; equals brute force over every subset (16 seeds x 4 chests) | `bestMatchesBruteForce` |
| Packing rules | `pack` / `unpack` / `close`: UNKNOWN, ALREADY_PACKED, TOO_HEAVY, NOT_PACKED, DUPLICATE, IGNORED | `guards` |
| Quest `q_keepsake_chests` | colony `QuestProgress`: pack keepsake x3, close warm x1 (HEAVY can be fixed), talk keeper_oriel | `questHeavyChestThenWarmThenKeeper` |

## Keeper Oriel's lines (`KeeperChestLines`)

- Greeting: "One chest a family, and the boat won't take a pound over. Choose what you'll miss most."
- Packing: "2 in the chest, 7 of 11 weight."
- Heavy: "It shuts, but there's a lighter way to carry more of home: 31 memory where 50 would fit. Open it and try
  again."
- Quest done: "Every chest closed warm. They'll unpack the whole island on the far shore."
- After: "The chests are roped down. The boats can go."

## Editor later (UNREAL-QUEUE)

Open sea chests on the jetty with a weight gauge, keepsake props laid out by each house (quilt, kettle, fiddle, seed
tin, lantern, jar of sand), and a lid-closing moment that glows warm. Source-only here.
