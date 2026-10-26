# G47 Ark Route Odds (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/route/`.
Reuses `world.odds.OddsRng`, `world.odds.Intervals` (Wilson), `world.odds.BalanceLimits` and the G22
`world.odds.weather.Sky`. Read-only on `world.ark`; this is not G24 (drydock), G29 (cargo) or G43 (seed vault).

## Story

After the asteroid, the arks were the only way to carry life off the shattered surface. Every launch
had to cross the belt, and there were only three charted ways through: the short, deadly **Shard
Narrows**, the weather-bound **Squall Lanes**, and the slow **Long Drift**. The Odds Keeper of the
inn (G18) kept the old launch ledgers, and still chalks the routes whenever an ark readies to sail:
which way brings the most souls home?

| Story beat | Mechanic in code |
|---|---|
| Each stretch of the belt has one hazard: debris holes hulls, squalls wash pens away, drift burns rations | `Hazard` (loss fraction 0.50 / 0.25 / 0.10) and `RouteLeg` (base strike chance, capped at 0.95) |
| Squalls follow the storm glass (G22); debris and drift do not | `Hazard.skyFactor`: SQUALL legs x0.5 CALM, x1 SQUALL, x2 STORM |
| A route is a chain of legs with souls aboard | `ArkRoute`: exact `cleanChance` and `expectedLifeHome`, seeded `sail` |
| The Keeper chalks which route brings the most life home | `RouteOddsBoard.simulate`: seeded race over all routes, best-route chance, fair odds, mean life home, clean-voyage Wilson interval |
| The house takes a small edge, never more than 10% | `RouteOddsBoard.clampEdge` / `postedOdds` (never below evens; never-winning routes are off the board) |
| The Keeper will not take bets on a lock | `RouteOddsBoard.postable(BalanceLimits)`: favourite's chance within [1 - maxPWin, maxPWin] |
| The player backs a route and the ark bell rings | `ArkRouteWager` quest stages and Keeper lines |

## Quest q_ark_route_wager

1. ODDS_POSTED: "Chalk favours <route> at N% to bring the most life home. The belt does not care who is aboard."
2. STAKED: "Herbs on the ledger. Ring the ark bell and let the belt decide."
3. BACKED_WINNER: "Your route brought the most souls home. That is what the arks were for." Pays stake x posted odds (rounded down).
4. BACKED_LOSER: "<route> brought more life home this time. Read the glass before the next launch."

The default routes (`ArkRouteWager.ODDSREAPER_ROUTES`, 120 souls each) are balanced so that, on a SQUALL
day, expected life home is about 92 / 99 / 101: no route is a lock, and a STORM sky pushes the
favourite off the Squall Lanes. Stakes are in-game storm herbs only; there is no real-money wagering.

## Determinism

Board trial `t` uses `OddsRng.forTrial(seed, t)`; the real voyage uses a fresh `new OddsRng(voyageSeed)`.
Within a trial, routes sail in listed order with one draw per leg. Ties on life home go to the
earlier-listed route.

## Editor / asset needs (later, not in this PR)

- Route board prop at the inn (can reuse the G18 parlay chalkboard with three route rows).
- Ark bell barks for the Keeper lines.
