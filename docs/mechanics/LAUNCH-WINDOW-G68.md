# G68 The Launch Window (OddsReaper Island / Sky Islands arks)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/launch/`.
Composes G22 (`world.odds.weather.StormGlass`, `Sky`) and G47 (`world.odds.route.ArkRoute`) read-only, plus
`world.odds.OddsRng`.

## Story

The arks did not just pick a way through the belt; they picked a day. Captains read the storm glass
at dawn and argued: launch now into a falling glass, or wait a day at anchor while the sick list
grows? The Odds Keeper keeps the old launch logs, and on launch mornings he chalks every option.

| Story beat | Mechanic in code |
|---|---|
| The glass is read at dawn | `LaunchPlanner.forecast`: G22 posterior from the climate, pushed `day` steps through the storm chain |
| Every day at anchor costs souls | `waitKeep` per day (2% lost per day on OddsReaper Island) |
| The Keeper chalks every route and day | `LaunchPlanner.options` / `expectedLife`: sum over sky of P(sky) x G47 expected life home x waitKeep^day |
| The Keeper's pick | `LaunchPlanner.best` (ties to the earlier day, then route) |
| Captains who launch within 2% of the chalk get the Keeper's nod | `LaunchWindowQuest.wise` (`TOLERANCE` 0.98) |
| The ark bell rings | `LaunchWindowQuest.sail`: launch-day sky drawn from the forecast, then the G47 voyage, then wait cost |

## Quest q_launch_window

1. FORECAST: "Glass reads LOW. Chalk says <route>, <today / tomorrow / in N days>, about N souls home."
2. CHOSEN: wise: "A fair launch. The old ark captains would have signed it." Otherwise: "Your call, captain. Chalk had N souls on <route>."
3. SAILED: "Launched under a <sky> sky on <route>: N souls home."

A LOW glass keeps the arks off the Squall Lanes today; debris and drift routes do not care about the glass.
No wagering here: the quest grades the captain's choice.

## Determinism

`sail(seed)` uses one fresh `new OddsRng(seed)`: the first draw picks the launch-day sky, then the route's legs draw
in order (the G47 `ArkRoute.sail` contract).

## Editor / asset needs (later, not in this PR)

- Launch log page on the inn's G18 chalkboard; ark bell bark.
