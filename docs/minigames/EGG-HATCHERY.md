# Egg Hatchery (PORT06 / WZ24) - contest gap G06

Owner: art-master-flex. Continues Claude's egg props (`tools/blender/voxel_eggs.py`, 49 egg types x Intact/Cracked/Hatching).

- Core: `daedalus-core/src/main/java/com/daedalus/world/eggs/EggHatchery.java` (pure, JDK-only, deterministic per seed).
- Data: `data/eggs/egg-hatch-v1.json` = `voxel_eggs.manifest()` export + a `care` block (warm band 36-39, crack 6, hatching 12, hatch 16, chill penalty every 3, perfect-care shiny x2).
- Test: `daedalus-core/src/test/java/com/daedalus/world/eggs/EggHatcheryTest.java` (13 tests).

## Rules
Each care tick: warmth in band = +1 growth (+2 if the egg is turned); out of band = chill, every 3rd chill costs 1 growth but never drops below the current stage. Stages follow growth thresholds; at `hatchAt` the family is rolled from the egg's weighted hatch pool, shiny at `shiny_odds` (doubled for zero-chill care).

## Daedalus tie-in
Shell pattern sets the hatchling coat (speckle/dots Spots, stripe/bands/zigzag Stripes, marble/spiral Labyrinth, else None), the same coat key Kennel Isle's `TonicBrewer` reads, so a hatchling can drink trough tonics as soon as it joins the companion roster. Eggs come from Colony Ledger fishing/scavenge/festival finds.

## Later (editor, not in this PR)
Nest/incubator actor + stage mesh swap (Prop_Egg_<Type>_<Stage>) via BOARD\UNREAL-QUEUE.md.
