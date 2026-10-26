# Sky-island fishing rules (contest gap G07)

Owner: oddsreaper. Module: `daedalus-core/src/main/java/com/daedalus/world/fishing/` (JDK-only, no editor).
Continues Team Claude's Prismheart pond (`data/rpg/prism-fish.json`, `tools/rpg_demo/index.html` `castLine`/`fishTick`)
and the ADR-066 colony-ledger fishing spots.

## What it does
| Class | Job |
|---|---|
| `FishTable` / `FishSpecies` / `Rarity` | Reads any `daedalus.rpg-fish/v1` table. `pick(u, conditions)` is the demo's `pickFish`, draw for draw. |
| `Conditions` | Day, night (night weights) and the **OddsReaper Island storm**: RARE/LEGENDARY bite 2x as often, bites come at 0.75x the wait and last 0.85x as long. |
| `CastSession` | One cast as a host-ticked state machine: WAIT (1.2 + u*2.4 s) -> BITE (fish window) -> DONE with TOO_SOON, GOT_AWAY, CAUGHT or REELED_IN. Seeded by the Combat Odds Engine's `OddsRng`, so replays hook the same fish. |
| `FishLog` | Counts per kind, "NEW!" on first catch, `3 / 6` progress, sale value for the inn menu. |
| `AnglerSkill` | Reaction ~ Normal(mean, sd); exact catch chance = normal CDF at the bite window. |
| `FishingOdds` | Exact per-cast odds and expected gold, a seeded Monte Carlo check with a 95% Wilson interval (`odds.Intervals`), and the **Storm Parlay**: chance and fair multiplier of landing named fish on consecutive casts. |
| `IslandFishery` | Sky-island spots (lake, stream, pier, sky_river, ocean_basin), seasons and the 06-10 / 17-21 rise; native fish come from island chemistry `water.fish`, visitors from the spot (`data/rpg/skyisland-fish.json`). |
| `FishingDemo` | `FishingDemo [fish.json] [seed] [casts]` prints day / night / storm odds for Windmere's pond. |

## Daedalus tie-in
An island's seed chemistry decides which fish live in its lake; the spot and the hour add visitors; a storm over
OddsReaper Island tilts the odds toward the big fish but shortens every bite. Catches feed the fish log, the inn menu
(price) and the day book. The Storm Parlay is an in-game inn board priced at fair odds; no real-money anything.

## Later (editor / art)
Rod, float and bobber props and a cast/bite actor go to BOARD\UNREAL-QUEUE.md and the Blender asks after this lands.
