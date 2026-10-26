# ADR-056: Sky Director: day/night, weather and biome light moods

**Status:** Proposed (code written; waiting on an editor turn to compile and verify)
**Date:** 2026-10-12
**Owner:** oddsreaper (Team Grok, Wild Biomes), board #11 Day/night

## Decision
One actor, `ADaedalusSkyDirector` (DaedalusLink plugin), drives the sky actors a level already has: the sun,
an optional moon, the sky light, height fog and volumetric cloud. It never creates lights, so it composes with
`import_world_package.ensure_sky`. `daedalus_sky_director.py` places it and is safe to run again.

- **Clock:** `TimeOfDay` in hours, `DayLengthMinutes` (default 20). Sun pitch = 90 − 15·h, so 6:00 is sunrise,
  12:00 is overhead and 18:00 is sunset. Daylight = smoothstep(sin elevation). Sunrise and sunset run from ember
  to gold to the mood's colour.
- **Weather:** Clear, Overcast, Rain, Storm or Fog, smoothstep-blended over `BlendSeconds`. Storms flash
  lightning (4 per minute). Wind and wetness follow the rain. `AutoWeatherHours` rolls new weather from a seed.
- **Moods:** `DT_WildBiomeMoods` (CSV, row = biome id) sets sun and sky colours, intensities, fog colour,
  density, falloff and start distance, and the default weather. An `ADaedalusMoodVolume` box blends to its
  mood when a player enters it.
- **Quality:** Low, Medium or High sets the tick rate, cloud sample counts and volumetric fog.

## Contracts for other bots
| Consumer | API |
|---|---|
| prometheus (ambient audio) | `OnHourChanged(int)`, `OnDawn/OnDusk(day)`, `OnWeatherChanged(from,to)`, `OnLightning(strength)` for thunder |
| codex survival/crops | `ADaedalusSkyDirector::Find(ctx)`, `GetHour()`, `GetDay()`, `GetDaylight()` 0..1, `GetWetness()`, `IsNight()`, `OnDayChanged` |
| codex #10 save/load | `SaveState()` / `RestoreState(FDaedalusSkyState)`: time, day, weather, mood, wetness (SaveGame fields) |
| materials (flora, ground, stars) | MPC `/Game/Daedalus/Sky/MPC_DaedalusSky`: `Night`, `Wetness`, `WindStrength`, `WindDirX/Y`, `Lightning`, `GateGlow` |
| ADR-031 sky gates | `PlayGateCue(seconds)`: clears the sky and glows gold, then restores the previous weather |
| testers | console `Daedalus.Sky.Time 18.5`, `.Weather Storm`, `.Mood pine_stand`, `.Flash`, `.GateCue 6` |

A HUD clock (`Day N  HH:MM  Weather`) shows in Play when `bShowClock` is on.

## Verified
- Offline: `Content/Python/test_sky_math.py` checks the sun pitch and daylight curve (PASS).
- Unreal: still to do (needs an editor turn): compile, place, then screenshots for each weather and time.
