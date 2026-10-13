# SUCCESSION — Pythagoras original mechanic + adventure (Team Grok)
Built on real ecology (Richey: ecology degree, 15 yr agronomy). Engine: `ecology_rules.py` / `island_flora.py` (already in game data).

## Core mechanic: steer living succession
Every island tile has a **seral clock** (years since last disturbance): 0 pioneer herbs -> 1 meadow -> 2 scrub/pine -> 3 climax oak forest.
The clock runs on its own (1 in-game day = 1 ecological year). The player never "places trees"; they **shape the process**:
| Lever | Action | Ecological effect |
|---|---|---|
| Disturb | axe a gap, windthrow storm event | gap clock -> 0 (pioneers flood in) |
| Burn | controlled fire with Fireweed torch | patch -> 0, soil +fertility, clears Bramble |
| Graze | move the sheep/goat pen | holds meadow at stage 1 forever; goats eat Bramble |
| Rest | fence out animals | succession resumes, scrub creeps in from edges |
| Water | dig stream channel | creates riparian band (Willow, Sedge) by distance to water |
| Seed | carry seeds from a neighbour island by Ark | adds species to the pool (island biogeography: far islands start poor) |
Rules are the real ones: moisture and slope niches, competition spacing (Clark-Evans), shade tolerance (oak waits under pine).
What you get depends on **which stage is where**: herbs, berries, timber, honey, creatures all need a stage.

## Payoffs
- **Succession Tea** (herb combo): herbs are stage-locked, so a full 0-1-2-3 ladder needs an island mosaic that holds all four stages at once. Mosaic = skill.
- **Creatures follow habitat**: hens need scrub edge, bees need meadow flowers, deer need old forest, frogs need riparian band. Pets' Turing coats tint by home biome.
- **Biodiversity score** per island (Shannon index of species x stages) feeds island value for the NFT holder and Ark trade prices.
- **Neighbour effects**: seed rain drifts downwind to linked islands; a burnt neighbour gives you pioneer seeds, a climax neighbour gives you acorns.

## Adventure: The Climax Seed
After the asteroid, no island holds a climax forest; the old oaks' seed is lost. The Ark crew finds a dead acorn ("the Climax Seed")
in the Pythagoras island archive. To wake it the player must **rebuild succession in order** on their island:
1. **Ash Field** — clear the impact scar; plant Fireweed, Yarrow (stage 0). Brew first tea: Pioneer Tea.
2. **Meadow Keepers** — bring sheep by Ark, graze a meadow; install bees. Learn grazing holds succession.
3. **Bramble Wall** — rest the land; scrub closes in and hides Hen Thieves. Goats or fire to open paths (choice: fire = fast, loses honey for 3 days).
4. **Pine Shield** — pioneer pines nurse young oaks under shade (real facilitation). Protect saplings from a windthrow storm event.
5. **Riverbank** — dig the stream; willows stabilise banks; frogs return; water chain becomes drinkable.
6. **Climax** — a 0-1-2-3 mosaic exists at once. Brew Climax Tea at the old stump: the Climax Seed sprouts a Great Oak (island landmark, unique per token seed).
Ending hook: Great Oak acorns can be carried by Ark to other players' islands — the first cross-island ecology chain.

## Build status / mapping to code
- Rules + per-token islands + disturbance gaps + biome recipes: done (`ecology_rules.py`, `island_flora.py`, `wild_biomes.py`, tests green).
- Herb combo data: `herb_combo.json`. Island with all five biomes, water chain, livestock: Island_Pythagoras (in Unreal).
- Next: `succession_sim.py` (tile seral clocks + levers, deterministic, tested), then UE hook to swap biome meshes as clocks advance.

## Depth (succession_depth.py, tested)
- **Island biogeography:** species pool grows with island area and shrinks with distance to other islands; pioneers always arrive on the wind.
- **Seed rain:** linked islands send wind seeds (pine, fireweed, grass) easily; acorns barely travel, so oaks need the Ark or jays. That makes Ark trips matter.
- **Windthrow storms:** old forest tiles fall (8% per storm) and become fresh gaps, so a climax island naturally re-opens into a mosaic.
- **Nurse facilitation:** oak seedlings only establish next to a stage-2+ tile (nurse pine/scrub), so you have to grow pine before oak, as in real secondary succession.
- **Quest progress:** `quest_progress(island, flags)` checks the Climax Seed chapters in order against the sim plus UE world facts.

## Chapter 7 - Seed Rain (epilogue)
The Great Oak drops one Climax Seed, but acorns only travel ~0.6 km and the bare islet is 2 km out. `colonise()` (succession_depth.py) settles the islet: wind seed rain as usual, every Ark Raft cargo species arrives for sure, and each Jay Feeder gives a 50% chance per crossing that jays cache acorns there (real jays move acorns km-scale). Goal: 2 Jay Feeders + 1 Ark Raft placed and 4+ islet species including Oak. 48 new props in pyth_items4.py (ClimaxSeed, JayFeeder, AcornCache, ArkRaft, IsletBeacon, SeedPod, ColonistCairn, SeedSorter); 714 glbs total. Tests: succession_depth 11/11.

## Chapter 8 - Fire Keeper
Intermediate-disturbance hypothesis as a lever: tiles burn with rate p per year (fire_keeper.py). No fire -> all oak (H=0); yearly fire -> all grass; H peaks near p=0.02-0.04 (1.31 at 0.02 vs 0.38 at 0.32). Goal: place the Fire Altar and set a burn rate whose mosaic H >= 1.2. 42 props (pyth_items5.py; 756 glbs). UE hook: hidden TriggerBox per chapter (PYT_QuestTrigger_<id>, tags PYT_Quest + Quest_<id>) and read-only pyth_quest_ue.py that derives quest flags from placed actors.

## Chapter 9 - Keystone Beaver
Beaver dams flood stream cells into wetland (keystone_beaver.py). One dam adds a habitat (H 1.35 -> 1.51); two dams placed downstream of the oaks reach H 1.56 with all 30 old-growth cells; dams by the oaks drown them (30 -> 18), three dams over-flood. Goal: 2 dams, H >= 1.55, old growth >= 30. The UE quest hook reads live dam positions as sim cells. 30 props (pyth_items6.py). Tests: test_keystone_beaver 5/5, full 9-chapter playthrough in test_quest_hook.
