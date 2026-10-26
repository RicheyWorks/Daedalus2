# G93 Storm-Herb Futures (OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/futures/`.
Composes G22 (`world.odds.weather.StormGlass`, `StormChain`, `Sky`) read-only. No randomness of its own: settlement
uses the island's seeded sky (`StormChain.skyOn`), so every player on one island seed settles the same way.

## Story

Storms flatten the herb beds on OddsReaper Island, so storm herbs (the island's trade token) are
dearest after a storm. Mossa the herb grower lost a whole season's income the year the arks
docked in a calm week and the price fell through the deck. Now the Odds Keeper runs a forward desk:
growers can sell their harvest ahead at a price set by the dawn reading of the storm glass.

| Story beat | Mechanic in code |
|---|---|
| Herbs are dearest after a storm | `HerbMarket` spot: CALM 10, SQUALL 14, STORM 22 |
| The fair price ahead follows the glass | `HerbMarket.fairForward` = forecast-weighted spot (G22 posterior pushed through the chain); `spotVariance` |
| Far-off days forget today's glass | forwards converge to the climate price |
| The Keeper quotes a bid and an ask | `FuturesDesk.bid` / `ask` (spread capped at 10%) |
| Contracts settle on the real sky | `FuturesDesk.settle`: `Forward.payoff` at the delivery-day spot from `StormChain.skyOn` |
| Mossa locks in half her harvest | `HerbHedgeQuest`: selling h of 20 bundles scales revenue variance by ((20 - h) / 20)^2 |

## Quest q_herb_hedge

Harvest 20 bundles on day 3.

1. QUOTED: "Glass reads <reading>. I'll take Mossa's day-3 bundles at N each, forward."
2. HEDGED: half or more: "Half the harvest or more locked in. Mossa sleeps tonight." Otherwise: "Mostly open. Mossa is betting on the weather now, not on herbs."
3. SETTLED: "Harvest settled under a <sky> sky: N tokens to Mossa."

In-game tokens only; there is no real-money trading.

## Editor / asset needs (later, not in this PR)

- Forward desk ledger next to the G18 chalkboard; Mossa NPC at the herb beds.
