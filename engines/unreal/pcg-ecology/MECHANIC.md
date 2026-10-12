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
