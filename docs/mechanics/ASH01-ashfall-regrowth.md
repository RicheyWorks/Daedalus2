# ASH01 Ashfall Regrowth (minigame core)

Owner: pythagoras (contest gap G20, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/AshfallRegrowth.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/AshfallRegrowthTest.java` (14 cases).
It reuses the Reactive Battlefield Ecology field and fire rules (ADR-061, `BattlefieldEcology`, `Vegetation`) and the
succession bands of `engines/unreal/pcg-ecology` (meadow, then bramble, then pine, then oak, with willow by the water).

## Story (shattered-planet canon)

When the meteor struck, the world shattered into a lane of floating islands (`docs/landmarks/ImpactSite.md`). The
fragments nearest the impact were scorched to glassy ash: no seed, no root, nothing to come back from. The arks
(ADR-019) carried life off the dying world, and every ark hold kept a seed vault for this day.

You berth beside a scorched fragment. The springs still run, and the ark's seed keeper hands you the last caches.
Ash stays ash unless something living stands close enough to seed it. Lightning still walks the dry season, and young
growth burns fast. Bring the fragment back to old forest before the fires take it again.

## Quest `q_ashfall_regrowth`

| Step | Trigger (what the core reports) | NPC line |
| --- | --- | --- |
| 1 Arrival | `scorch(...)`, `fuel() == 0` | **Seed keeper Ilsa** (`npc_ark_seedkeeper`): "Six caches. That is all the hold kept. Ash will not seed itself, so set them where the green can reach the rest." |
| 2 First green | a `seedCache` returns > 0 | Ilsa: "There. Every season the green walks two strides further. Leave a gap wider than that and it never crosses." |
| 3 Carry water | a `water` call returns true | **Spring tender Oru** (`npc_spring_tender`): "Water from the spring makes it grow twice as fast, and wet ground will not burn. You can only carry it four strides from water, three loads a season." |
| 4 The herd | a `graze` call returns true | **Herder Bram** (`npc_ark_herder`): "My goats crop the bramble and keep the turf short. Fire dies on it. But nothing they graze ever grows into forest." |
| 5 Dry lightning | `Season.struck()` | Ilsa: "Lightning. Young meadow is the worst kindling there is. Oak and willow barely burn." |
| 6 Willow by the water | first `Band.WILLOW` | Oru: "Willow at the water's edge. It never burns. That is your firebreak for good." |
| Win | `Outcome.RESTORED` | Ilsa: "Old forest on a fragment that was glass. The ark can sail on." Reward: `lore_ashfall`, the keeper's `seed_vault_key` |
| Lose | `Outcome.SCORCHED` | Ilsa: "It burned again, and we have no caches left. Some fragments the sky keeps." (Retry with a new seed.) |

## Rules (all deterministic from the field, settings, seed and moves)

1. **The scorch.** `AshfallRegrowth.scorch(field, settings, seed)` takes a `BattlefieldEcology` field. Its WETLAND cells
   are water (springs, pools, shore). Every other cell is burnt to ash (BARE).
2. **Seed rain.** Ash greens to meadow only if a living cell lies within `seedReach` (2 cells). With no seed cache,
   the fragment stays sterile forever, and a test proves it.
3. **Succession bands.** Each season is 4 years. A cell climbs ASH, MEADOW, BRAMBLE (SCRUB), PINE, OAK using the
   ADR-061 stage years (1, 4, 15, 40). Meadow next to water (within 1 cell) grows into WILLOW carr (WETLAND), which never burns.
4. **Ark seed caches** (6 per run). Each one turns the ash within 1 cell of it to meadow at once.
5. **Carried water** (3 loads per season, only within 4 cells of water). A watered 3x3 patch grows at double speed
   and cannot burn that season.
6. **Grazing herds** (2 per run, permanent). A herd crops its 3x3 patch: bramble goes back to meadow and stays there,
   and the cropped turf does not carry fire. The trade-off is that a grazed patch never becomes forest.
7. **Fire risk.** After growth, lightning strikes with chance `strikeChance x fuel`. Fuel is the mean flammability of land that
   would carry fire, so young meadow (0.60) is the most dangerous and oak (0.12) and willow (0) the least. Bare ash never
   draws lightning. The fire burns under a random dry wind using `BattlefieldEcology.tick()`, and every burnt cell goes back to ash.
8. **End.** RESTORED when 40% of the land is old growth (oak or willow). SCORCHED when fires have burnt 75% of the
   land in total. The run ends after 40 seasons; if neither has happened by then, the outcome is GROWING.

## What the tests prove

Sterile ash without caches; the seed-rain front spreading 2 cells per season; dry ground climbing the bands in order;
willow beside the water that never burns; carried water reaching pine sooner but refused far from a source and capped
per season; a grazed strip holding a wind-driven fire that crosses an ungrazed one; fuel highest in young meadow;
bare ash never struck by lightning; the full toolkit (caches, herds, water) restoring at least 19 of 20 seeds and burning
less than caches alone; an unguarded recovery that can be scorched again; determinism; the host field mirroring every
band (cover, DBE 1 snapshot); finite budgets and bad input refused.

## Host seam (Unreal, later)

The field you pass in is the live field. Read it with `UDaedalusEcology` through `Dbe.write(field)` (DBE 1), so the
PCG island and cover queries see the regrowth. Call `seedCache/water/graze` from player interactions and `season()`
on a day or season tick. `strike(x, y)` takes combat fires, e.g. from DBE-E 1 IGNITE events.
Assets staged NOT READY by blender-team (2026-10-19, link 48889) in `bot-team\staging\contest-20261019\`:
`Prop_Ash_SeedCache` (frame) with `Prop_Ash_SeedCache_Lid`, `_Closed` and `_Open` states, and `Prop_WaterBucket`; the herd reuses the Mob livestock from catalog.bba; flora are the pcg-ecology bands. Front axis: Blender -Y lands on UE +Y, placement yaw -90. The editor binding goes in `BOARD/UNREAL-QUEUE.md`.
