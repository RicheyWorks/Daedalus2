# The Treasure Scales: Youtube Master Island, chapter 63 (youtube-master, contest G368)

Chapters 1-62 run from melody brewing (G25) to the berry patch (G360) and the festival rites (G363). A trader's ship
comes for the festival.

## Story

The trader weighs goods on a scale that takes only so much. Keeper Oriel asks the player to load the island's
treasures as close to the limit as possible without tipping it. Taking the heaviest pieces first can leave the scale
light. A LIGHT load, an OVER load, or a bad pick earns no credit.

## Beats, mechanics and tests (`TreasureScalesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hoard | `seeded`: 1-12 treasures of weight 1-50, cap 0-200 | `seededHoardIsDeterministic` |
| Closest load | `best()`: meet-in-the-middle (half subset sums, sort, binary search); equals brute force over every subset (30 seeds) | `bestMatchesBruteForce` |
| Heaviest first is a trap | weights 8, 6, 5, 5 and cap 10: 8 alone is LIGHT; 5 + 5 is 10 | `heaviestFirstIsLight` |
| Over or bad | `load` OVER the cap or MALFORMED (repeat or unknown pick), no credit | `overAndMalformedEarnNoCredit` |
| Scale rules | `load`: MALFORMED, DUPLICATE, IGNORED | `guards` |
| Quest `q_treasure_scales` | colony `QuestProgress`: weigh treasures x1, load best x1 (retries allowed), talk keeper_oriel | `questLightThenBestThenKeeper` |

## Keeper Oriel's lines (`KeeperScaleLines`)

- Greeting: "4 treasures and a trade scale that takes 10 weight. Load it as close to 10 as you can without going over."
- Light: "That load is 8. You can get to 10."
- Over: "That's 14. The scale tips past 10."
- Quest done: "As close as it goes. The trader shakes your hand."
- After: "The trade is made. Good weight."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A brass trade scale on the jetty, a pile of island treasures, and the trader's ship. Source-only here.
