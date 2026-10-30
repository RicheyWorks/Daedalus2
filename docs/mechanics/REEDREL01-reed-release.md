# REEDREL01 - Reed Release (contest G507)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/ReedRelease.java`
Tests: `ReedReleaseTest` (7 tests, including an exhaustive brute force). Source only; no Unreal, no new assets.

## Story / Daedalus hook

G251 taught Pip to release cranes early. G504 warned that planting too much reed feeds hawks and starts
boom-and-bust swings. Now Pip makes both choices together: a planting order for the G183 meadow crew (how many
hectares of reed) and a release calendar for the G163 aviary (8 cranes over 4 years, at most 4 a year).

## Model

Each season runs the G504 hawk/crane Rosenzweig-MacArthur equations with RK4 (20 steps a year). Released cranes
join at the start of a season, and a seeded log-normal shock hits the cranes at its end (sigma 0.15, mean 1).

A run crashes if cranes fall below 4 at any census after the releases. Every plan is scored on the same 150 shock
paths (common random numbers), so the comparison is fair and replays exactly.

`best()` tries every reed option and every schedule. `fast()` builds a greedy schedule for each reed option.

## Default result (start 6 cranes, 3 hawks, 40 seasons)

| Reedbed | Best schedule | Crash risk | No releases |
|---|---|---|---|
| 10 ha | [4,4,0,0] | 0.00 | 0.00 |
| 25 ha | [4,4,0,0] | 0.11 | 0.13 |
| 40 ha | [4,2,2,0] | 0.76 | 0.75 |
| 55 ha | [4,4,0,0] | 0.93 | 0.95 |
| 80 / 110 / 150 ha (above Hopf, 64.3 ha) | - | 1.00 | 1.00 |

The lesson for the quest: the Hopf point is not the safety line. Hawks still drive damped swings well below it,
and those swings push a young flock under the crash level. The safest marsh plants little reed, releases early,
and lets the flock settle. This is the paradox of enrichment seen through a crash threshold.

## Tests (ReedReleaseTest, 7)

1. `best()` equals the brute-force minimum over every reed option and every schedule (nested loops in the test).
   It spends the whole budget, and its risk replays.
2. Greedy is never better than exact and is within 0.03 of it.
3. The best reed is below the Hopf hectares. Every option above Hopf is at least as risky as every option below
   it (about 1.0).
4. More reed never lowers the best risk (0.02 tolerance).
5. Releases help on a 25 ha reedbed compared with releasing nothing.
6. Seeded plans replay exactly.
7. Bad tuning and schedules are rejected.

## Assets

None. Reuses the G504 / G142 marsh. The marsh hawk mob is still an optional Blender ask.
