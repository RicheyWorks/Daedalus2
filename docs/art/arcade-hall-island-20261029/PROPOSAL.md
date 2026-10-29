# Arcade hall island siting - proposal + hook (2026-10-29)

Read-only survey of com.daedalus.world.island (IslandPlan, IslandGenerator, LandGenerator, IslandOps, IslandTraits).
No island data, generator code or golden values were changed.

## Hook (implemented, off by default)
`com.daedalus.world.arcade.ArcadeHallSite` - pure, read-only function over an IslandPlan.
- Flag: system property `daedalus.arcadeHall.islandSites` (default off). `siteIfEnabled` returns empty when off.
- `find(plan, layout)`: per-column top-cube map; footprint must be all land (GRASS/SAND/DIRT) with height spread <= 1;
  a 2-column approach strip in front (-Z), length ceil(0.9 + 3*1.6) = 6 cubes, must be land within 2 cubes of the floor.
  Picks the candidate nearest the island origin (deterministic).
- Returns Site(layoutId, minX, minZ, width, depth, floorY, doorAnchor, pathStart).

## Safety
Nothing in island generation calls the hook, so generated islands are byte-identical by construction.
ArcadeHallSiteTest pins IslandGeneratorTest's golden seed-11 digest with the flag on and after siting, and checks sites
are flat, clear and deterministic (sites found across seeds 1..40).

## Next step (not done - needs owner sign-off)
Place hall pieces from the Site in the world/scene layer (not in IslandGenerator) so island digests stay untouched.
