# G77 The Rival Book (OddsReaper Island / ark docks)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/rival/`.
Reuses `world.odds.OddsRng`, G56 `world.odds.ledger.KellyStake.edge`, and reads G47 `RouteOddsBoard` chances in tests.
Read-only on G35/G47/G56.

## Story

Not every survivor trusted the Odds Keeper's chalk. When the arks docked above OddsReaper Island, a
rival bookmaker set up his slate on the ark docks, copying the Keeper's boards with his own margin
and his own mistakes. The Keeper does not argue with him. He hands newcomers his fair chances and
asks them to find the soft lines.

| Story beat | Mechanic in code |
|---|---|
| The rival copies the Keeper's chances, adds his margin, and misprices each line | `RivalBook.post`: odds = 1 / (p x (1 + margin) x e^u), u uniform in [-spread, spread], seeded |
| A soft line pays more than the chalk says it should | `ValueScan.values`: lines with edge p x odds - 1 above a threshold (G56 `KellyStake.edge`) |
| Between the Keeper's slate and the rival's, sometimes every outcome pays | `ValueScan.isArb` / `arbSum` (sum of 1 / best price below 1) and `arbStakes` (equal-return split) |
| Call every soft line before he catches on | `RivalBookQuest`: two miscalls and he wins |

## Quest q_rival_book

1. SCANNING: "N of his lines are soft and you have found M. Check them against my chalk."
2. EXPOSED: "Every soft line called. He will think twice before pricing my arks again." Pays 15 storm herbs.
   If the rival made no soft lines: "Not a soft line on his slate today. Even a rival gets lucky." (no reward)
3. FOOLED (2 miscalls): "He priced you as well as the routes. Read the chalk, not his smile."

Value threshold: edge above 2%. Herbs are in-game only; there is no real-money wagering.

## Editor / asset needs (later, not in this PR)

- Rival's slate prop on the ark docks; rival bookmaker NPC (reuse an inn villager mesh).
