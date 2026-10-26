# G80 The Ark Underwriter (OddsReaper Island / Sky Islands arks)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/insurance/`.
Composes G47 (`world.odds.route.ArkRoute`, `ArkRouteWager.ODDSREAPER_ROUTES`) and G22 `Sky` read-only; reuses
`world.odds.OddsRng` and `Intervals`. Not G24 (drydock), G29 (cargo) or G43 (seed vault).

## Story

After the first arks were lost in the belt, the survivors on OddsReaper Island made a promise: no
family would be left with nothing when an ark came home short. The Odds Keeper ran the pool. Every
ark paid a premium before launch; every lost soul's family was paid from it. Price too dear and the
survivors cannot launch; price too thin and one bad season breaks the pool.

| Story beat | Mechanic in code |
|---|---|
| Each ark buys cover for its souls | `ArkPolicy`: pays `coverPerSoul` per soul lost on its G47 route under the day's sky |
| A fair premium is the expected loss | `ArkPolicy.expectedClaim` = cover x (aboard - G47 expected life home) |
| The Keeper adds a loading, never more than 50% | `ArkPolicy.premium(loading)` (clamped, whole herbs) |
| One season: every insured ark sails once | `UnderwritingPool.season` (G47 `ArkRoute.sail`, policy order, one stream) |
| How often does a season break the pool? | `UnderwritingPool.simulate`: seeded insolvency chance (Wilson) and mean profit |
| Fair to the survivors, safe for the pool | `UnderwriterQuest.quote`: loading <= 25% and insolvency <= 5%, else rejected |

## Quest q_ark_underwriter

Reserve 80 herbs, six arks (two per belt route), cover 1 herb per soul, 2,000-season board.

1. QUOTING: "Six arks, one season. Price the cover fair to them and safe for us."
2. REJECTED: too dear: "Survivors cannot pay that. Bring the loading down." Too thin: "N% of seasons break the pool. Price it thicker." (Quote again.)
3. APPROVED: "Approved: N% bust risk, about N herbs expected profit. Ring the bell."
4. SOLVENT: "Season closed with N herbs in the pool. Every lost soul's family was paid."
5. BUST: "The pool broke. The arks paid for it once already; never again."

Herbs are in-game only; there is no real-money insurance or wagering.

## Editor / asset needs (later, not in this PR)

- Pool ledger page on the inn counter; ark bell bark.
