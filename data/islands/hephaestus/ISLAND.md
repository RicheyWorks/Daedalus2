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

Capture path (in `heph_island_ue.hero_capture`, loaded at turn start via runpy): warm SceneCapture2D (exposure bias +1, white temp 5200 K, bloom 0.4) → if that fails, set viewport to this pose, settle 2s, HighResShot 1920x1080 + Shot, copy newest Saved/Screenshots PNG to `hero_r2.png`. `heph_turn` prefers that file over bridge `viewport_screenshot` (which timed out on round-1).

## Win condition
Water running, pens producing, herb beds watered, and at least one dual-quenched tonic in the player's pack. The Great Forge glow brightens when all three living systems are up — the shard is tempered.
