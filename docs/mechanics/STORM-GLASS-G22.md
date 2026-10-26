# Storm Glass forecast (contest gap G22)

Owner: oddsreaper. Module: `daedalus-core/src/main/java/com/daedalus/world/odds/weather/` (JDK-only, no editor).
Feeds G07 fishing (`Conditions`) and the G18 Storm Parlay board.

## Story
OddsReaper Island sits on the storm line of the Shattered Planet. Storms linger once they arrive, and calm mornings
break into squalls. On the inn wall hangs a brass **storm glass**: honest, but noisy. A calm day still reads FALLING
one time in five. Each morning the Odds Keeper taps the glass, works out the odds of a storm, and chalks her Storm
Parlay board for the day's real sky. Her second quest, **Read the Glass**, asks a newcomer to call the storm five times
or more with a mean Brier score of 0.20 or better. The reward is a pocket storm glass.

## Mechanics (each story beat is code)
| Beat | Code | Rule |
|---|---|---|
| The storm line | `StormChain.ODDSREAPER` | 3-state Markov chain CALM / SQUALL / STORM; storms stay 50%. |
| Same storms for everyone | `StormChain.season / skyOn` | Day d draws from `OddsRng.forTrial(islandSeed, d)`. |
| The island's climate | `StormChain.climate()` | Stationary distribution (power iteration). |
| The noisy glass | `StormGlass.read / readOn` | P(reading given sky) matrix; seeded per day. |
| Reading the glass | `StormGlass.posterior / forecast / stormChance` | Bayes update, then roll the chain forward n days. |
| Read the Glass quest | `ForecastScore` | Brier score, skill against the climate almanac, `questPassed()`. |
| Storms feed the games | `StormDay.conditions / sky / board` | A full STORM sets G07 `Conditions.storm`; the G18 board is priced for the real sky. |

## Later (editor / art)
Storm-glass barometer prop on the inn wall: UNREAL-QUEUE.md and a NEED to blender-team after landing.
