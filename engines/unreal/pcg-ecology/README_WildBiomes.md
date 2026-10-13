# Wild Biomes (Team Grok) — PCG flora & ecology

Rule-based ecology (Richey: ecology/agronomy grounded) placing real Blender-team flora on Daedalus floating islands.

| File | Role |
|---|---|
| ecology_rules.py | pure-python niche model: moisture (stream distance), slope, succession (years since disturbance), competition spacing. Self-tests. |
| island_flora.py | token_id -> deterministic island profile (succession age, stream course, seed). One unique flora layer per NFT island. |
| wild_biomes.py | 5 biomes (YoungMeadow, BrambleScrub, PineStand, OldGrowthOak, WillowRiverbank) via site selection over the rule model; patch size + density scale with island size. |
| island_bounds.py | measures real island footprint with ray probes (works after islands are scaled). |
| wild_biomes_ue.py | editor job: sublevel /Game/Pythagoras/Maps/WildBiomes_Pythagoras, places biomes, habitat TriggerBoxes (tags DAEDALUS_Habitat, Habitat_<biome>), saves sublevel; saves persistent only if it was clean before. |
| flora_economy.py | species -> harvest drops (hardwood, resin, willow_bark, fiber), validates economy recipes. |
| live_pcg.py / native_graph.py | PCG graph build (Python-precomputed) and native-node graph (CreatePointsGrid -> Projection -> density filters). |
| test_wild_biomes.py | biome distinctness, area scaling, determinism. |

Run: `python ue_send.py wild_biomes_ue.py 600` (on your editor turn only).

## UE PCG findings
- PCG does nothing unless the PCG plugin is enabled in the .uproject (classes load, generate() silently no-ops).
- No Landscape: SurfaceSampler is useless on voxel islands; use CreatePointsGrid + Projection (world ray hit).
- Output node input pin is labelled "Out". GetActorData needs select_multiple + GET_SINGLE_POINT for markers.
- Grid cell size/extents are in volume-local space: divide by volume scale or you get millions of points.
- Native graph is weaker than the Python model for succession (trees under-represented); Python layout kept for now.
- Pet habitat: query actors tagged `Habitat_<biome>` (TriggerBox) for spawn/roam zones.
