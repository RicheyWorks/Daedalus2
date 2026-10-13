# Hephaestus Island (Team Grok, hephaestus)

Theme: the forge island — a 1024 m volcanic planet-shard whose core took the asteroid's direct strike. Twice normal size. Manifest: `data/islands/hephaestus.json`. Pack: `layout.json`, `water.json`, `herbs.json`, `livestock.json`.

**ARK_ORIGIN:** `6000000, 2000000, 0` (cm). Sublevel: `/Game/Hephaestus/Maps/HephaestusIsland`.

## Storyline: the Shard That Learned to Temper

When the planet Daedalus shattered, most fragments flew cold. Hephaestus Island was the piece whose heart took the asteroid head-on. The impact melted the core into a living forge: magma that never quite cools, iron that remembers heat. The first ark crews did not flee it. They riveted stilts around the caldera, built the Great Forge on the molten heart, and learned that every hull that would ever fly had to be tempered here first.

The keepers carved one rule into the quench tub rim: **"Heat alone breaks. Water alone softens. Temper both, or the ark dies in the void."** That rule is Forge Temper — the island's unique herb mechanic — and it is also how the settlers live: ash fields feed the pens, pens fertilise the beds, springs feed the forge and the troughs, and the drydock turns ore and rivets into arks that leave carrying life to other shards.

Story beats for players:
1. **Arrival (thirst first):** you land at the basalt coast thirsty. Caldera heat drains thirst x2. Drink only at HotSpring_Clean or a cooled QuenchTrough_Forge; the ash well is dirty until boiled.
2. **The pens:** emberhens, ashgoats, forgeox, lavaboar, cinderwool and vent bees starve for trough water. Fill RanchTrough_Ash from the spring pipe and the product loop starts (eggs, milk, wool, honey, truffles, bellows work).
3. **Forge Temper:** brew a tonic at the mortar, then quench it magma, spring, or dual. The quench path is the island's signature — strength, duration, or both pair effects.
4. **The drydock:** rivet an ark hull with starmetal and emberite from the Meteor Scar. The Great Forge glows when water, livestock and herbs all run — the island's "tempered" win condition.
5. **q_forge_temper:** prove you can dual-quench a tonic, water the pens through a forge shift, and leave one ark plate stamped with your mark.

## REALM: Forge Reach
Volcanic planet-shard forge-yards where asteroid iron meets living magma. Survival through tempering, quenching, and ark drydock trade. Heat shimmer and ash wind shape discovery; riveters keep daily schedules.

## MECHANIC: Forge Temper (unique to Hephaestus)

Herb tonics are tempered by **quench path** after brewing (mortar / hand-mix, then quench). Detail: `data/islands/hephaestus/herbs.json`. Shared essence pairs: `data/herbs/combos.json`.

| Path | Strength | Duration | Station | Feel |
|------|----------|----------|---------|------|
| **magma** | x2 | x0.5 | `Prop_ForgeQuenchTub_Basalt` (hot) | brief fierce temper |
| **spring** | x0.5 | x2 | `HotSpring_Clean` or cooled quench trough | long soft temper |
| **dual** | base + **dual effect** | base | magma then spring (or reverse) within 10s | primary pair **and** next-best pair both land |

Rules:
- Every tonic consumes 0.5 L of clean water at brew time.
- Magma-quenched tonics overheat the drinker unless they take a cooled trough sip after.
- Ashgoat slag-grass grit fertilises herb beds (+10% growth).
- Herb plants need 1 L/day or pause growth; Steamreed and Boilbalm only grow if a vent or spring watered them that day.
- Island signature herbs in the beds: Emberleaf, Ashmint, Cinderroot, Forgefern, Lavathistle, Kilnpoppy, Pyreweed, Steamreed, Boilbalm, Hearthbasil, Ventmoss, Coalclover (full list in herbs.json).

### Example dual-quench
Brew Emberleaf (cool+iron) + Forgefern (calm+heat) → primary pair effect from combos.json. Dip magma, then spring within 10s → primary **and** the next-best matching pair both apply at base strength/duration. That is the Forge Temper signature players chase for ark expeditions.

## Livestock / food loop

| Animal | Eats | Gives | Drinks |
|--------|------|-------|--------|
| emberhen | grain, seeds, Emberleaf leaves | egg every 10 min | 0.5 L/day RanchTrough_Ash |
| ashgoat | hay, herbs, slag-grass | milk every 20 min; grit fertilises beds | 8 L/day |
| forgeox | hay, grain | milk every 25 min; pulls bellows (+15% forge speed) | 12 L/day |
| lavaboar | scraps, mushroom, turnip | truffle 30% / 30 min | 6 L/day |
| cinderwool | hay | wool every 30 min (shears) | 6 L/day |
| vent_bees | flowering herbs within 15 m | honey every 40 min | 1 L/day dew |

Unfed/unwatered animals stop producing after 1 day and leave after 3 (cozy rule: never die). Detail: `livestock.json`.

## Survival loop
1. Drink at HotSpring_Clean; caldera heat is the real clock.
2. Pipe spring water to RanchTrough_Ash and QuenchTrough_Forge.
3. Ash fields grow herbs (Forge Temper beds) and hay; slag-grass on the cooled rim fertilises beds.
4. Animals give eggs, milk, wool, honey, truffles; forgeox works the bellows.
5. Brew and quench tonics for heat resist, clarity, and ark work.
6. Mine Meteor Scar (starmetal + emberite), rivet at the drydock, leave on an ark that remembers this forge.

## Drinkable water (Quench Network)

Detail: `water.json`. Hot spring alone (~1920 L/day) covers player + full ranch + herb beds.

| Source | Quality | Drink? | Notes |
|--------|---------|--------|-------|
| HotSpring_Clean | clean | yes | primary; heat zone nearby |
| SteamVentCatch | clean | yes | vent steam + rain |
| RainCatch_Ash | clean | yes | after 1 min settle |
| SaltStill_Basalt | clean | yes | salt + backup water |
| QuenchTrough_Forge | by fill | yes when cooled clean | magma side NOT drinkable until cooled |
| RanchTrough_Ash | clean | yes (also animals) | fed from spring pipe |
| AshWell_Dirty | dirty | no | boil/filter first |

Thirst: player 3 L/day base, x2 in caldera. Dirty drink = partial quench + sick chance. Animals without water for a day stop products.

## Zones
1. **Caldera Forge** — Great Forge, anvil ring, bellows (forgeox), quench tub.
2. **Meteor Scar** — asteroid + planet shards; starmetal + emberite.
3. **Ark Drydock** — half-built ark, rivet crates.
4. **Ash Fields** — herb beds + ranch housing.
5. **Livestock pens** — 16 head on Mob_ meshes + iron trough (by hot springs).
6. **Hot Springs** — clean water, steam vents.
7. **Basalt Coast** — salt still, lava tubes, black sand.
8. **Water chain** — pipes, catches, cistern props.

## Quest: q_forge_temper
Prove the island is tempered:
1. Dual-quench one tonic (magma↔spring within 10s).
2. Keep RanchTrough_Ash full through one forge shift (forge_quench demand 20 L).
3. Stamp one ark plate at the drydock with your mark (rivet crate interaction).
Reward: forge-tempered tonic recipe unlocked + drydock blueprint fragment.

## Layout / editor
- Blockout: `layout.json` — 119 placements (water 24, livestock 16, herbs 12 living tags).
- Turn kit: `tools/islands/hephaestus/heph_turn.py` + `heph_island_ue.py` (idempotent, own folder only).
- Preflight (headless): `heph_preflight.py` — all layout assets must resolve before a turn.
- Hero meshes: `heph_hero_glb.py` (procedural low-poly, no Blender RAM hit).
- Round-1 result (2026-10-12 ~18:43 PT): 119/119 placed, living check PASS, sublevel + DaedalusWorld saved; viewport_screenshot timed out (owed on round-2).


## Hero camera (round-2 shot)

Forge overlook — high three-quarter view of the Great Forge with drydock and hot springs behind.

| Field | Value |
|-------|-------|
| Origin (cm) | `6000000, 2000000, 0` |
| Cam relative (m) | `140, -160, 90` |
| Target relative (m) | `0, 0, 5` (Great Forge) |
| Cam world (cm) | `6014000, 1984000, 9000` |
| Target world (cm) | `6000000, 2000000, 500` |
| FOV | 55° |
| Stable PNG | `C:\Users\730ri\projects\bot-team\shots\hephaestus\hero_r2.png` |

Capture path (in `heph_island_ue.hero_capture`, loaded at turn start via runpy): SceneCapture2D exposure ladder (auto +1 → manual EV100 8 → manual EV100 5 → unlit base color; white temp 5200 K, bloom 0.4), each rung probed on a 9x9 pixel grid and kept at the first mean luma ≥ 20 (same gate as the NFT card; round-3 auto capture measured ~0.1), rungs logged to `bot-team\shots\hephaestus\hero_capture.json` → if that fails, set viewport to this pose, settle 2s, HighResShot 1920x1080 + Shot, copy newest Saved/Screenshots PNG to `hero_r2.png`. `heph_turn` prefers that file over bridge `viewport_screenshot` (which timed out on round-1).

## Win condition
Water running, pens producing, herb beds watered, and at least one dual-quenched tonic in the player's pack. The Great Forge glow brightens when all three living systems are up — the shard is tempered.

## Round-2 Unreal verification (2026-10-12 21:02 PT)

Editor turn after youtube-master HANDOFF #23780 (36s wall). Bridge preflight live; RAM ~9 GB free; imports skipped (all 72 assets already in Content).

| Check | Result |
|-------|--------|
| Placements | **119/119** (0 missing) |
| Living | water **24** / livestock **16** / herbs **12** |
| Sublevel | /Game/Hephaestus/Maps/HephaestusIsland at ARK_ORIGIN 6000000,2000000 |
| Saves | sublevel=True, DaedalusWorld+maps=True, dirty=[] |
| Hero shot | `bot-team\shots\hephaestus\hero_r2.png` (SceneCapture2D warm, 1920x1080, forge overlook) |
| Play check | 20s PIE OK; hero_unreal_play.png; Play stopped |
| HANDOFF | hephaestus → **pythagoras** at 21:03 PT |

Kit: Daedalus2 main `fa19daf9` (round-2 documentation commit). Contest still active.

## Off-editor polish (2026-10-12 ~21:24 PT)

Water budget audit + Forge Temper `temper_ev` (no Unreal / editor turn).

| Check | Result |
|-------|--------|
| Layout heads | emberhen 3, ashgoat 3, forgeox 2, lavaboar 3, cinderwool 3, vent_bees 2, herb_beds 12 (from `layout.json` Mob_/Item_Herb_*) |
| Demand (caldera stress) | **105.5 L/day** (player 6 + animals 87.5 + herbs 12; forge_quench 20 is shift-spike) |
| Supply | HotSpring_Clean **1920 L/day** (80 L/h × 24) |
| Margin | **1814.5 L/day** vs caldera-stress demand |
| claim_check | hot spring covers player + full ranch + herb beds for base **and** caldera, with or without forge_quench — **true** |
| temper_ev | all 36 herbs: magma P×2 / dur×0.5; spring P×0.5 / dur×2; dual P×1 + dual_effect; best_for_strength=magma, best_for_duration=spring |

## Off-editor polish (2026-10-12 ~21:36 PT)

Ranch production budget + Great Forge glow win meter (no Unreal / editor turn). Heads from layout.json; rates from livestock.json products.

| Product | /day (full care) | Notes |
|---------|------------------|-------|
| egg | 432.0 | emberhen ×3 every 10 min |
| milk | 331.2 | ashgoat + forgeox |
| truffle_mushroom | 43.2 | lavaboar 30% / 30 min |
| wool | 144.0 | cinderwool ×3 |
| honey | 72.0 | vent_bees ×2 |
| forgeox bellows | +30% forge speed | 2 head near bellows |

| Glow | Condition |
|------|-----------|
| cold | 0 of water / pens / herbs |
| ember | 1 living system |
| bright | 2 living systems |
| tempered | all 3 + dual-quench in pack |

Failure: unwatered/unfed 1 day → products stop; 3 days → animal leaves (cozy). Detail: livestock.json → production_budget.

## Off-editor polish (2026-10-12 ~21:47 PT)

Forge-atmosphere material contract + numeric Great Forge Glow score (no Unreal / editor turn; buffffff holds the editor). Nothing here has been applied in Unreal yet: `materials_mpc.json` is a data contract for the next Hephaestus editor turn (`"applied": false`).

**MPC_Heph_ForgeSky** (`materials_mpc.json`; source: Daedalus Sky Director + caldera heat zone + glow score; mirrors OddsReaper `MPC_OR_SkyWeather`):

| Param | Range / default | Drives |
|-------|-----------------|--------|
| HeatShimmer | 0–1 / 0.4 (1.0 in caldera) | heat distortion, thirst UI cue, basalt hot edge |
| AshFall | 0–1 / 0.25 (storm 0.8) | ash particles, ash-field film, haze |
| MagmaPulse | 0–1 / 0.5 (6 s sine) | Great Forge core emissive, magma pool, braziers |
| QuenchSteam | 0–1 / 0 (1.0 on dip, 4 s half-life) | steam at `Prop_ForgeQuenchTub_Basalt`, quench surface |
| NightForge | 0–1 / 0 (dusk 18→21 h) | anvil/forge rim light, spring underglow |
| TemperGlow | 0–1 / 0 (= score/100; 0.9 headless now) | Great Forge tempered look (ForgeTint lerp) |

Bindings: `MI_HotSpring` (**exists**, on `WaterPlane_HotSpring`; its BasicShapeMaterial parent only takes Color, so the apply turn needs a parent with emissive/opacity/roughness). `MI_Heph_ForgeIron`, `MI_Heph_Basalt`, `MI_Heph_QuenchWater`, `MI_Heph_AshSoil`, `MI_Heph_HerbLeaf` are **planned** MIDs.

**Great Forge Glow score 0–100** (`livestock.json` → `production_budget.win_meter.score_0_100`):

| Signal | Points | Today (data) |
|--------|--------|--------------|
| water_running (water.json claim_check.both_true) | +30 | true |
| pens_producing (16 head from layout) | +30 | true |
| herb_beds_watered (12 beds) | +30 | true |
| dual_quench_in_pack (q_forge_temper step 1) | +10 | quest-gated |

| Score | Glow |
|-------|------|
| 0 | cold |
| 1–39 | ember |
| 40–69 | bright |
| 70–99 | near-tempered |
| 100 | tempered |

Tempered win (data rule, no engine write): score == 100 held for 60 in-game minutes (`tuning.sustain_ingame_min`). Any signal dropping lowers the score at once and resets the timer. Glow lerps at 0.1/s into `TemperGlow`. The existing `glow_levels` and `signals` stay as they were.

Validators (headless):
- `tools/islands/hephaestus/heph_forge_glow.py`: read-only. Checks signals, score math, band coverage 0–100, the 36/36 herbs with `temper_ev`, and the MPC params and bindings. Result: **PASS**, score 90 (near-tempered) now, 100 (tempered) with dual-quench simulated.
- `tools/islands/hephaestus/heph_ranch_budget.py`: now also writes the score block and asserts 0/30/60/90/100 → cold/ember/bright/near-tempered/tempered.

## Off-editor polish (2026-10-12 ~22:10 PT)

NFT card + dual-quench signature cookbook (no Unreal / editor turn; pythagoras and make-ups hold the editor).

- **`nft.json`**: Hephaestus Island card 🔥⚒️, same shape as OddsReaper's. Traits: Mood forge_volcanic, Water Quench Network (HotSpring), Herbs Forge Temper (magma | spring | dual), the 6 livestock species, Items 119, Builder Hephaestus (Team Grok). Hero image: `bot-team/shots/hephaestus/hero_r2.png`.
- **`herbs.json` → `dual_cookbook`**: 8 signature dual-quench recipes, all using bed herbs. Each has the primary and next-best pair and effects from `data/herbs/combos.json`, quench dual, window 10 s, and the stations `Prop_ForgeQuenchTub_Basalt` + `HotSpring_Clean`. The `rank_rule` used to pick the pairs is written into the file. The existing `herbs` / `temper_ev` are unchanged.

| Recipe | Herbs | Primary | Next-best |
|--------|-------|---------|-----------|
| Riveter's Temper | Emberleaf + Forgefern | forge_speed_+25pct (iron+heat) | cold_resist (heat+calm) |
| Lava Runner | Boilbalm + Hearthbasil | fire_resist (heat+heat) | sprint_speed_+20pct (heat+vigor) |
| Caldera Canteen | Steamreed + Coalclover | thirst_restore_25 (purify+cool) | purify_water_x5 (purify+purify) |
| Quench Tub Draught | Emberleaf + Steamreed | thirst_restore_25 (purify+cool) | heat_shield (cool+cool) |
| Drydock Shift | Hearthbasil + Coalclover | forge_speed_+25pct (iron+heat) | harvest_power_+1 (iron+vigor) |
| Void Crossing | Forgefern + Kilnpoppy | cold_resist (heat+calm) | slow_hunger (calm+calm) |
| Ash Well Antidote | Pyreweed + Coalclover | thirst_restore_25 (purify+cool) | cure_poison (light+purify) |
| Scar Prospector | Cinderroot + Steamreed | thirst_restore_25 (purify+cool) | ore_luck_+10pct (clarity+iron) |

- **`hephaestus.json` `resources.herbs`**: now lists all 36 herb ids from herbs.json (it had 6).
- **Validator** `tools/islands/hephaestus/heph_dual_cookbook.py` (headless, read-only). It checks that the herb ids exist, both pairs are distinct combos keys (order-insensitive) with matching effect ids, both pairs can be formed from the two herbs' essences, `rank_rule` reproduces primary then next-best, quench is dual, the window is 10 s, the stations are right, and the manifest lists 36/36 herbs. Result: **PASS** (8 recipes, 11 effects covered). A tampered copy fails as it should.
- **Lore**: added `lore_forge_temper` to `data/lore/codex.json`: "Heat alone breaks. Water alone softens. Temper both."

## Off-editor polish (2026-10-12 ~22:45 PT)

NFT card now prefers the real Play hero shot (no Unreal / editor turn; disk-saver handed off to youtube-master for round-3). Mirrors OddsReaper `0ce8a09d`.

Why: the round-2 SceneCapture2D `hero_r2.png` came out near-black (1920x1080, mean RGB ~0.1). The 20s PIE Play shot `hero_unreal_play.png` (1280x720, mean RGB ~147/152/133) is a real lit frame. Play shot is from the PIE player view, not the forge overlook pose, so a proper overlook capture is still owed on the next editor turn.

| Field | Value |
|-------|-------|
| `hero_image` | `bot-team/shots/hephaestus/hero_unreal_play.png` (primary) |
| `hero_image_fallback` | `bot-team/shots/hephaestus/hero_r2.png` (round-2 SceneCapture forge overlook; use only if Play shot is missing) |
| `traits.HeroShot` | Play viewport (round-2 SceneCapture was near-black) |
| Name / sigil / blurb / other traits | unchanged; Items 119 |

Validator (headless, read-only): `tools/islands/hephaestus/test_heph_nft_card.py`. Checks name, sigil, blurb, traits (Mood, Water, Herbs, Livestock, Items, Builder), Items == 119 == `layout.json` placements, hero_image is exactly the Play shot and not hero_r2, fallback is hero_r2, and on BLACKBEARD that both PNGs exist under `C:\Users\730ri\projects\` with a PNG header. Result: **ALL PASS**. Existing validators re-run: `heph_dual_cookbook`, `heph_forge_glow`, `heph_ranch_budget`, `test_heph_give_up` all PASS.

## Round-3 editor turn (2026-10-12 22:50–22:51 PT)

After youtube-master HANDOFF #24366 (22:47:37). CLAIMed 22:48; `heph_turn.py --now` pid 32524 (stale armed waiter 37884 killed so it could not double-run).

| Step | Result |
|------|--------|
| Bridge preflight | 9877 alive; Play off; DaedalusWorld |
| RAM | 1.90 GB free; imports allowed (no new glbs needed) |
| Place | 119/119; living water 24 / livestock 16 / herbs 12; imported 0 |
| Save | sublevel True, maps True, dirty_maps [] |
| Hero SceneCapture | `hero_r2.png` 1920x1080 **still near-black** (mean RGB ~0.1) — overlook pose remaining |
| 20s Play check | `hero_unreal_play.png` 1280x720 **lit** (mean RGB ~147/152/133); Play stopped |
| HANDOFF | → pythagoras; editor saved, Play stopped; turn 38s |

Sublevel `/Game/Hephaestus/Maps/HephaestusIsland` at 6000000,2000000. NFT card already prefers the Play shot (`c924e60a`); SceneCapture overlook still owed when a lit forge-overlook capture works.

Also tightened `heph_turn.py` HANDOFF matcher: accept `HANDOFF hephaestus` (em-dash / direct address, as youtube-master posts) in addition to `HANDOFF … -> hephaestus`, so a waiting runner can start without `--now`.

## Off-editor polish (2026-10-12 ~23:05 PT)

Blender forge-overlook hero (no Unreal / editor turn; art-master-flex holds the editor after oddsreaper HANDOFF).

Why: round-2/3 SceneCapture2D `hero_r2.png` is still near-black (mean RGB ~0.1). The PIE Play shot is lit but not the forge overlook pose. Off-editor Cycles render on RTX 4090 OptiX fills the overlook gap the same way Prometheus did for their island.

| Field | Value |
|-------|-------|
| `hero_image` | `bot-team/shots/hephaestus/hero_blender.png` (primary; 1920x1080, mean RGB ~85/69/56, lum ~72) |
| `hero_image_play` | `bot-team/shots/hephaestus/hero_unreal_play.png` (round-3 PIE Play, lit) |
| `hero_image_fallback` | `bot-team/shots/hephaestus/hero_r2.png` (SceneCapture overlook; near-black; last resort) |
| `traits.HeroShot` | Blender forge overlook (SceneCapture still near-black) |
| Renderer | `heph_blender_hero.py` — layout 119 proxies + 7 hero GLBs from `hero_1625`, camera `hero_cam_m`, Cycles OptiX 96 spp, ~7 s |

Validator: `test_heph_nft_card.py` now requires Blender primary, Play secondary, r2 fallback, and primary mean luminance >= 20. SceneCapture overlook in Unreal is still owed on a later editor turn when a lit capture works; until then the mint card uses the Blender overlook.

## 23:20 PT heartbeat (off-editor): SceneCapture exposure ladder

Round-3 `hero_r2.png` was mean RGB ~0.1 (a SceneCapture has no eye-adaptation history, so auto exposure starts black at dusk). `heph_island_ue.hero_capture` now walks `EXPOSURE_LADDER` (auto +1, manual EV100 8, manual EV100 5, unlit base color), probes each capture with `read_render_target_pixel` on a 9x9 grid, exports the first rung at mean luma ≥ 20 (or the brightest), and only falls to HighResShot if all are dark. Headless check: `test_heph_capture_ladder.py` ALL PASS; `test_heph_nft_card.py` still ALL PASS. Runs on the next granted editor turn; not touching Unreal now.

## Off-editor polish (2026-10-12 ~23:33 PT)

Blender-team landmark wire-up (no Unreal / editor turn; round-3 closed, round-4 disk-saver on deck).

blender-team posted READY for QUEUE **1360–1366** (judged + turntables). Wired into `layout.json` so the next granted editor turn imports the seven GLBs and places them with the living island.

| QUEUE | Asset | Zone | Role |
|-------|-------|------|------|
| 1360 | `Prop_Asteroid_Core` (8×8×5 m, emissive veins) | meteor_scar | landmark |
| 1361 | `Prop_Asteroid_Chunk_Small` (~1.5 m) | meteor_scar | landmark |
| 1362 | `Prop_Asteroid_Chunk_Large` (~4 m) | meteor_scar | landmark |
| 1363 | `Prop_Crater_RimRock` (~3 m) | meteor_scar | landmark |
| 1364 | `Prop_ArkWreck_Hull` (20.7 m broken mid-hull) | ark_drydock | landmark |
| 1365 | `Prop_Grok_Monolith` (6 m orange/white) | caldera_forge | landmark |
| 1366 | `Prop_Grok_SeedPod` (4 m emissive band) | ash_fields | landmark |

- Placements: **119 → 126**. `nft.json` `traits.Items` = 126.
- `layout.landmarks` metadata holds queue rows + asset list.
- GLBs present under `bot-team/art/glb` (preflight should list them `glb_only` until imported).
- Validators: `test_heph_landmarks.py`, `test_heph_nft_card.py` (EXPECTED_ITEMS=126).
- Not touching Unreal. SceneCapture overlook + landmark import still owed on the next editor grant.
