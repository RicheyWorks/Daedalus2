# G152 Void Crossing

Contest gap G152 (minigame contest 2026-10-19, hephaestus). Source: `daedalus-core/src/main/java/com/daedalus/world/forge/VoidCrossing.java`, tests in `VoidCrossingTest` (10).

ISLAND.md ends the forge story with "leave on an ark that remembers this forge", and the quench-tub rim warns "temper both, or the ark dies in the void". G24 `ArkDrydock` decides whether an ark may launch. Void Crossing is the voyage that follows.

## Rules

- `VoidCrossing.depart(ark, voyage, tonic, spares, seed)` casts off. An ark that fails the G24 inspection is `NOT_LAUNCHED` and never sails. Spare rivets in the crate: 0..12.
- The weather is seeded and fixed at departure, so the crew's orders never change it. On about every other day a void storm strikes one seam for 15 to 40 strength, and on about one day in five a cold snap sets in. The host shows `today()` before the crew gives the day's order.
- Each day `sail(seam)` either patches one seam with a spare rivet (+10, the G24 `MISSING_RIVET_COST`, never past the seam's launch strength) or holds (`-1`).
- On a cold-snap day the crew cannot work unless they drank **Void Crossing** (`dual_void_crossing`, cold_resist + slow_hunger, from the island cookbook), and without it they drink double that day. The tonic also cuts the crew's own water by a quarter.
- The hold pays the day's water at the G24 rates (crew 20 dl each, plus every head aboard). On a day the hold runs dry, one head of the thirstiest kind aboard is lost.
- If any seam ends a day below 30, the hull breaches (`BREACHED`) and the ark limps home. Otherwise it arrives (`ARRIVED`), or `ARRIVED_WITH_LOSSES` if the hold ran dry.
- Captain Mira Sootvane of Storm Anchorage keeps the log line. `encode()` gives one `VXC 1` line.

`VoidCrossing.bosun(...)` is the reference crew: every working day it patches the weakest damaged seam. An ark loaded with exactly its G24 water need never loses a head on the tonic. Without it, cold snaps drain the hold. Better-tempered plates and a full rivet crate both cut breaches.

## Host contract

The host owns the `Crossing`, shows today's weather, and sends one order per day. A native C++ core will be its own claim.
