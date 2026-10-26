# Portal realm upgrade — first full art kit

2026-10-13. Art owner: Sol/team-codex. Unreal import, placement, binding and Play evidence: Claude/unreal-team. The source game is ADR-052 and `world.retro`; the additional art-role brief is `REALM-CASTS.md`.

The delivery contains **91 unique exports and 40,426 triangles**: 16 hero/town models, 48 monster/dragon visual models and 27 static environment/item meshes. It accounts for **33 distinct roles**, excluding duplicate palette tiers and the second dragon growth stage. This is a first art kit with motion prototypes; the existing game has not yet been converted to these models.

## Cast and gameplay boundary

Hero art forms: Knight, Tinker, Herbalist and Bard. Town art: Innkeeper Rusk, Smith Garra, Item Shop Pim, Queen of Cinders, Royal Scribe, Fortune Teller, Keymaker, Well Child, Night Watch, Retired Hero, Ferry Woman and Tavern Bard. Equipment and headwear distinguish their silhouettes. The Tavern Bard has a different cape, brim and instrument trim from the travelling hero Bard.

The existing engine's NPC contracts are TALK, NEWS, INN, SHOP and QUEEN. Bind the new art to generated NPC records, prices, stocks and map-derived lines. The named art does not implement new shops, a save-point NPC, a ferry, or a four-member combat party by itself. The existing three-member party is unchanged. Four role forms need a reviewed native/server mapping before becoming playable party members.

All humanoids share a 14-bone rest skeleton. Idle, Walk, Attack and Hurt clips are exported. Walk has four authored key phases with a closing pose; Unreal should verify the intended stepped presentation after import. Attack/Hurt are recovery loops and pose prototypes; they do not implement hit timing, damage, weapons or status effects. No sprite atlas, facial rig, IK, cloth or root-motion controller is claimed.

## Source bestiary and visual tiers

The actual Java enum contains fifteen types: BLIGHT_SLIME, BOG_SLIME, LUCKY_DRIP, DUST_WISP, EMBER_WISP, SHARDBACK, GLASSBACK, PUFFCAP, SHADECAP, GLOOMWING, STARE_ORB, GNASHBOX, MOSS_KNIGHT, STONE_KNIGHT and SHARD_TYRANT. Every one has three visual tier exports. Each carries its source key, source-file SHA256 and visual-tier number.

These 45 models are **15 source types**, not 45 new species. Source HP, attack, defence, agility, rarity, drops and traits remain authoritative. A cosmetic tier cannot grant extra stats or stand in for the independently rolled shiny trait. The existing Lucky Drip encounter remains unchanged.

Golden Puffcap is additional proposed art. No encounter probability, reward or engine entry was added. The earlier roster's “about once in fifty” description must be reviewed alongside the existing Lucky Drip distribution before implementation.

The other two proposed models are Egg Hatchling and Young Dragon, counted as one dragon lifecycle role. They have a common `PortalLandDragon` lifecycle group. The expected egg identity remains the same through intact/cracked/hatchling/young stages; the art does not mint tokens, transfer ownership, consume an egg or create an extra NFT. Native gameplay and the blockchain team must implement that boundary.

All 48 creature models share eight bones with Idle/Walk/Attack/Hurt clips. Motion is a rigid-part prototype; source-specific flying, slime movement, quadruped stepping and combat polish remain open. The hatchling's recommended actor scale is 0.65; canonical export rest transforms stay compatible.

## Environment and items

The 27-piece kit covers seven field terrain tiles, town/castle/cave walls, entry frames, shop counter, inn bed, smith anvil, throne, stairs, key chest, bronze/silver/star gates, portal arch, stage section, egg nest and two egg-state item meshes. Field/floor tiles use one metre units; walls and stage sections state their actual dimensions through the GLB. The display `.blend` is a contact-sheet arrangement, not a map or final gameplay layout.

Every prop/tree is joined into one mesh before export, including a forest tree's trunk and crown. There are no `_Top` companion meshes to place separately. This follows Claude's recent tree-assembly correction. Collision, navmesh, lock interaction, stairs transitions and material effects require explicit native setup.

Reused assets were also checked: shared keys and healing/shield/stamina potion meshes exist in the bot-team catalog. `data/art/portal/reuse-candidates.json` records actual paths/hashes and their proposed uses. These references are not counted as newly built exports or silently assigned effects. Existing item definitions and the detailed item workbook remain the source for mechanics.

## Story and mechanics: The Road of Small Wonders

This chapter connects the review storyline's first rainbow trip to the existing Portal progression. Its new dialogue and connective scenes are proposals; the established impact-shattered world and map/key rules are preserved.

**Arrival.** The rainbow's sparse dust leads to a small blue-topped arch. The travellers take this realm's visual forms. The Well Child describes the town using clues from the generated map. The player learns that a friendly hint should point toward a reachable place, not an invented compass direction.

**A useful town.** Rusk offers rest at the real inn price; Garra and Pim use the generated gear/item stocks. The Royal Scribe can present existing save state once bound, but a promised save must only appear after durable completion. The Tavern Bard plays a short travelling refrain through the touring jukebox. Matching text and a visual cue keep the clue accessible without requiring hearing or particular audio hardware.

**A borrowed road.** The proposed Bard clue mission sends the player to two existing landmarks before revealing a map-derived route hint. It should grant knowledge or a reviewed realm reward, not a critical key that the generator already places. The prototype avoids duplicating the key/chest engine. The Ferry Woman's role is an optional route lesson until an actual crossing contract exists.

**Keys with consequences.** Bronze, silver and star gates use the existing consumable-key rules. Chest visuals reveal the chosen outcome only after the authoritative engine resolves it. A mimic is an encounter, not a second client-side loot roll. The castle visit and three cave depths remain the existing progression; the star key is not obtained through a new cosmetic tier or purchase.

**A companion in an egg.** The intact and cracked shells let owners recognise the same egg through growth. Proposed care interactions involve clean water, safe shelter and patient visits, with the two dragon models as visible milestones. Care values, offline growth, ownership transfer and rewards need a later shared contract. The companion is distinct from a random enemy encounter; hatching must not replace the owner's deed or duplicate the egg token.

**Return.** The player returns to the same rainbow carrying earned knowledge and realm-specific items. The Queen's source blessing and defeat/respawn behaviour remain authoritative. A Golden Puffcap sighting can later add wonder without replacing Lucky Drip or making a financial/reward promise. Cross-realm transfers stay explicit and reviewed.

Halloween décor and friendly carnivorous helper plants remain in Labyrinth. Portal uses original adventure imagery, without moving Halloween props or adding the proposed undead Bone Drake here.

## Pipeline and verification

Generators: `portal_cast.py`, `portal_monsters.py`, `portal_environment.py`, sharing `portal_common.py` and the owned primitive/rig helpers. Run Blender in background with `-- OUTPUT`. Then run `validate_portal_package.py OUTPUT`.

Validation checks all 91 IDs and actual GLB hashes/counts, the animated models' accessors, skin weights, joints, matching rest transforms, finite motion and loop endpoints, and the static props' lack of accidental skin/animation. Source-key coverage requires exactly fifteen enum types and tiers 1/2/3 for each. A changed source enum/hash is refused until reviewed.

Cross-realm modular reuse was verified: the Portal humanoid joint rest transforms match Labyrinth Wayfinder, and Portal creature transforms match Labyrinth Corner Rat. Claude can attempt to reuse those two skeleton assets after verifying import scale/axes and skin binding. This avoids treating the visual realm styles as separate rig technology. Native retargeting is still unproven.

The combined production workbook appends 91 Portal rows to the existing 67 Labyrinth rows. Existing Labyrinth data/editable statuses are preserved. A role-count column prevents palette tiers and dragon stages inflating species/character counts. Portal now shows 33 roles and 64 validated animated visuals; Play proof remains zero in this delivery tracker. Formula/status change-and-restore checks pass; the edited sheets were rendered and inspected.

Local delivery root: `C:/Users/730ri/Documents/Codex/2026-10-13/portal-buildout/`. Package: `portal-buildout-91.zip` in its parent. Source manifest, catalog upsert rows and behavior bindings are committed under `data/art/portal/`. BBA uses `lod1 -`: no reduced mesh is delivered. Existing static BBA tooling must not be assumed to implement skeletal LODs.

## Claude acceptance

1. Import by mesh type; verify one-metre units, forward orientation, the two rest rigs and all four clips. Reuse existing skeletons only after an actual import test.
2. Build a small Portal review scene with field/town/castle/cave pieces, all hero/NPC roles and representative tier ladders. Confirm assembled plants, wall/stair seams and actor scales.
3. Bind only the fifteen source monster keys and generated NPC contracts initially. Golden Puffcap, four-member party behaviour and dragon lifecycle stay feature-gated until their contracts exist.
4. Demonstrate one inn/shop/hint interaction, one existing battle, a key gate/chest outcome and a cave transition through authoritative game state. Record video/screenshots plus source and manifest hashes in the registry/workbook.

Open work includes refined species animation, full interaction wiring, collision/nav, inventory tab skin/icons, directional sprite treatment if required, quest/reward/save binding, egg ownership/growth, rainbow effects, native audio placement and performance acceptance. Gallery City, Parcels and Bricks follow in the agreed order.
