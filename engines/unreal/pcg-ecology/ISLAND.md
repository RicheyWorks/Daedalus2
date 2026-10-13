# island:pythagoras — Wild Biomes ecology island (Team Grok)
120 m island (double size) at (-600 m, 600 m), sublevel `/Game/Pythagoras/Maps/Island_Pythagoras`, built by
`Daedalus2-pcg-ecology/engines/unreal/pcg-ecology/pyth_island_ue.py`. Art: 512 Blender items (`pyth_items.py` -> `art\glb\pythagoras`).

## Biomes (ecology model, real succession rules)
YoungMeadow (4 yr), BrambleScrub (15 yr), PineStand (45 yr), OldGrowthOak (240 yr), WillowRiverbank (stream). Each patch has a
habitat TriggerBox tagged `DAEDALUS_Habitat` + `Habitat_<biome>` for pets/NPC spawns.

## Drinkable water (hard rule) — gravity chain, 3 independent sources
| Stage | Actor | Role |
|---|---|---|
| W1 | Spring | aquifer spring, 30 L/min, never dry |
| W2 | Stream_00..11 | carries spring water through the willow riverbank (willow/sedge band follows it) |
| W3 | Pond | 40 m3 store; raw water |
| W4 | ReedFilter | constructed wetland: reeds + gravel turn raw -> drinkable (removes Murky) |
| W5 | Well | backup into the same aquifer |
| W6 | Cistern | 2,000 L drinkable store |
| W7 | RainBarrel x4 | rain catch, 20 L per rain tick each |
| W8 | Troughs (pen) | livestock drink here |
Demand ~35 L/day (player 3, sheep 4x5, hens 0.3x6, cow 8, goats 4x2); spring alone covers it, rain + well cover a blocked spring.

## Herb combo: Succession Tea (unique to Pythagoras)
Every herb belongs to a **seral stage** where it grows wild: 0 pioneer (Fireweed, Yarrow, Plantain), 1 meadow (Selfheal,
Meadowsweet, Comfrey), 2 scrub (Nettle, Mullein, Valerian), 3 forest (Woodsorrel, Ramsons, Wintergreen).
Steep 2–4 herbs. The **sequence** of stages is what matters, like a real succession:
1. **Ladder** (consecutive stages, e.g. 0-1-2): effect strength x1.0 per rung climbed; a full 0-1-2-3 ladder = Climax Tea
   (all stats +15%, 10 min).
2. **Gap** (skip a stage, e.g. 0-2): brew is "disturbed": half strength but the effect lasts twice as long.
3. **Reset** (a later stage followed by stage 0, e.g. 3-0): Fire Tea — clears debuffs, then gives a short pioneer burst (+speed).
4. **Site bonus**: brewing inside a biome whose seral stage matches the highest herb doubles duration (YoungMeadow=0/1,
   BrambleScrub=2, PineStand=2, OldGrowthOak=3; Riverbank counts as 1 and adds +water regen).
5. Each herb sets the stat: Fireweed regen, Yarrow heal, Plantain poison cure, Selfheal heal-over-time, Meadowsweet pain/stamina,
   Comfrey bone/defense, Nettle strength, Mullein lungs/stamina, Valerian sleep/calm (taming), Woodsorrel hunger, Ramsons
   immunity, Wintergreen cold resist.
Data: `herb_combo.json`.

## Livestock + food loop
| Animal | Lives | Eats | Gives | Food |
|---|---|---|---|---|
| Sheep x5 | meadow pen | meadow grass, hay | wool, milk | cheese, wool -> rope/cloth |
| Goats x2 | pen | bramble browse (keeps scrub from closing) | milk | cheese |
| Cow x1 | pen | grass, hay | milk, manure | milk pail, manure -> herb beds |
| Hens x6 | scrub edge coops | seeds, insects | eggs | egg basket, herb bread |
| Bees x5 hives | wildflower meadow | flowers (pollinate herbs +yield) | honey, wax | honey jar, tea sweetener |
Grazing is an ecology lever: grazed meadow stays stage 0-1 (no succession), ungrazed meadow scrubs over in-game days.

## Round 2 editor turn (2026-10-12 22:01-22:03 PT)
- pyth_fix_ue: 84 chapter glbs imported, 34 PYT_Chapter props placed, 7/709 actors trace-snapped (worst 35.4 cm), grass M_PYT_IslandGrass_v3, broken M_PYT_IslandGrass deleted.
- pyth_verify_ue: 796 actors; water chain W1-W8 OK (19 drinkable); livestock 5 sheep/2 goats/1 cow/6 hens/4 bees + full food loop (8 foods); 12 herbs, stages OK; biomes YoungMeadow 176, BrambleScrub 70, PineStand 57, OldGrowthOak 53, WillowRiverbank 148. Ground fit: 29 still >5 cm off (worst 85 cm), to fix next.
- Camera anchors for youtube-master: PYT_Label_<biome>, PYT_Habitat_<biome> (tag Habitat_<biome>).
