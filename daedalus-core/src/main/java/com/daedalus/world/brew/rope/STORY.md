# The Rope Market: Youtube Master Island, chapter 24 (youtube-master, contest G212)

Chapters 1-23 run from melody brewing (G25) to the lost verse (G204) and the lantern parade (G209). The boats leave
the spring and put in at a harbour town.

## Story

The harbour market buys rope by the piece, and the stall pays a different price for every length; some lengths are
bargains and some are not. The fleet has a coil to spare from the Rope trader (G66). The player cuts the whole coil
into pieces (or splices a piece back), then sells. Pieces that fetch the most possible make a rich sale; anything less
is thin.

## Beats, mechanics and tests (`RopeMarketTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The stall's prices | `seeded`: a 6-12 length coil, prices rising 0-4 per length with the odd bargain | `seededMarketIsDeterministic` |
| The best price | `bestPrice()`: rod-cutting DP; equals brute force over every way to cut (30 seeds); `bestCuts()` walks it back and uses the whole coil | `bestPriceMatchesBruteForce` |
| The whole coil isn't always best | lengths 1-4 pay 1, 5, 8, 9: two 2s fetch 10, the whole coil 9 | `theWholeCoilIsNotAlwaysBest` |
| A market that pays nothing | zero prices: selling is still the best possible | `zeroPricedLengthsCanStillBeSold` |
| Cutting rules | `cut` / `join` / `sell`: UNKNOWN, TOO_LONG, NOT_CUT, ROPE_LEFT, DUPLICATE, IGNORED | `guards` |
| Quest `q_rope_market` | colony `QuestProgress`: cut piece x3, sell rich x1 (THIN can be fixed by splicing), talk keeper_oriel | `questThinThenRichThenKeeper` |

## Keeper Oriel's lines (`KeeperRopeLines`)

- Greeting: "They pay by the piece here, and not every length is worth the same. Cut the whole coil, and cut it to
  fetch the most."
- Cutting: "1 pieces cut, 3 left on the coil."
- Ready: "All cut. Take it to the stall."
- Thin: "That fetched 7 where 10 was there for the cutting. Splice and try again."
- Quest done: "Every bit of that coil sold at its best. We'll eat well tonight."
- After: "The rope's sold and the purse is full."

## Editor later (UNREAL-QUEUE)

A harbour rope stall with a price board by length, a coil on a measuring bench with chalk marks, and cut pieces laid
out on the counter. Source-only here.
