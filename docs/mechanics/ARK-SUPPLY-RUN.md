# Ark Supply Run (contest G29)

Contest gap **G29** (minigame contest 2026-10-19, owner 2hot2trot). It codes the life-progression hook
"**Ark Supply Run**: animals coordinate bounded cargo" from *What Life Learns*
(`docs/mechanics/LIFE-PROGRESSION-AND-MINIGAMES.md` on the life-progression branch). It is a source-only Java core,
and no editor work was done. All numbers are **proposed** and need owner tuning.

Code: `daedalus-core/src/main/java/com/daedalus/world/ark/supply/`
(`Cargo`, `Passenger`, `CrewMember`, `SupplyRequest`, `SupplyRun`, `SupplyRunAdapter`), tested by `SupplyRunTest`.

## Story

The asteroid broke the old routes. Every raised island launches an ark, and new islands need seed caches, water and
timber before anything can grow there. The ark carries survivors as passengers, and they must be fed and watered
for the whole crossing. An animal crew (an Easel Mule, ark goats, a big ox) carries the cargo up the gangway, and
those animals learn logistics from real runs. Peaceful work is a full growth path.

## Rules

| Rule | Detail |
| --- | --- |
| Voyage length | `ArkFleet.duration(fromBerth, toBerth)`, the same timing the live arks use. Rations are drawn per started **watch** (15 s of sailing). |
| Passengers | Each needs `waterPerWatch` casks and `fodderPerWatch` bales; colonies can need none. Rations come off the top before any request counts. |
| Hold | `HOLD_KG = 1000` kg and `HOLD_VOLUME = 120` crate slots. Cargo: water cask 10 kg/1, fodder bale 5/2, seed cache 2/1, salve jar 1/1, timber bundle 20/4. |
| Crew | Each animal carries `carryKg` per trip for `maxTrips` trips; loading past the crew's total returns `CREW_TIRED` (they rest; nobody is overworked). |
| Requests | `SupplyRequest.forIsland(seed)`: 2..4 seeded requests, always seed caches first and water second, never the same cargo twice. |
| Check | `check()` lists water/fodder shortfalls and the request ids still short, so the UI can say exactly what is missing. |
| Delivery | `deliver(now)` settles once on arrival: passengers eat and drink in order, then requests are filled in order. A second call returns the same `Delivery`. |

## Progression (G12)

`SupplyRunAdapter` (activity `ark.supply-run`) credits the crew (profiles animal, bird, social_insect; roles
carrying, logistics, guarding) once per run through `ActivityResultReceipt` + `ProgressionLedger`. A complete
delivery is `COMPLETED`, a short one is a settleable `FAILED` (effort still counts if a policy allows), and a run
abandoned at the pier is `ABANDONED` and pays nothing.

## Pending

- Unreal: cargo crates on the ark deck and a gangway loading interaction (UNREAL-QUEUE after landing).
- Owner decisions: hold limits, ration rates, request ranges, award numbers.
