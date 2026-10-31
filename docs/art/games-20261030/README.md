# Game items, Prism Shard Dev batch (2026-10-30)

Blender items for 11 Prism games, built by `tools/blender/games/game_items.py` (blender-kit/v1) and staged NOT READY in `bot-team/staging/games-20261030/<game>`.

| Game | Assets | Kit | Sheet |
|---|---|---|---|
| glowmoss | 15 | data/games/glowmoss.kit.json | glowmoss.png |
| spiritkite | 8 | data/games/spiritkite.kit.json | spiritkite.png |
| glimmerloom | 12 | data/games/glimmerloom.kit.json | glimmerloom.png |
| shadewatch | 9 | data/games/shadewatch.kit.json | shadewatch.png |
| shardfall | 11 | data/games/shardfall.kit.json | shardfall.png |
| prismcairn | 8 | data/games/prismcairn.kit.json | prismcairn.png |
| wardens_accord | 9 | data/games/wardens_accord.kit.json | wardens_accord.png |
| facetlock | 10 | data/games/facetlock.kit.json | facetlock.png |
| prismvault | 5 | data/games/prismvault.kit.json | prismvault.png |
| lumenpath | 9 | data/games/lumenpath.kit.json | lumenpath.png |
| shardring | 12 | data/games/shardring.kit.json | shardring.png |

Build: `python tools/blender/games/game_items.py --game <g> --kit data/games/<g>.kit.json` then `blender -b --factory-startup --python tools/blender/kit/build_kit.py -- --set data/games/<g>.kit.json --out <dir>`.

Notes
- Every asset has sockets.json sidecars (UE convention); check_kit and engines/sidecar_cpp report 0 problems.
- Each game has a shared upright arcade cabinet with sockets Floor, Screen, Marquee, Player1 and CoinSlot. This covers the marquee audit (58760).
- NPCs (Mob_*) and the spirit kite tail are static placeholders; rigs pending. Sockets: Floor, Head, HandR, HandL, Speak.
- All items NOT READY until art review.

## star_mesh (art-master-flex, READY 59021)

8 assets: orrery cabinet, star chart table (inlaid grid), star peg lit/unlit, chart thread (1 m, scale X to the edge length), sighting glass, flip tally board, Mob_StarMesh_NavigatorWren (static, rig pending). Sheet: star_mesh.png.

## fog_channel_pilot (2hot2trot, READY 59012)

21 assets: foghorn cabinet, pilot boat, 4 lane buoys (bob about the Pivot socket), foghorn, 4 echo glyph discs (dull, ring, clang, silence), drifting ship silhouette, 3 fog bank cards (calm, fog, pea soup), lane chart board (4 x 16), 3-star plaque, harbour gull (perch and glide), Harbour Pilot and Dockhand NPCs. The gull and NPCs are static, rigs pending. Sheet: fog_channel_pilot.png.

## shardsong_crossing (prometheus, READY 59004)

15 assets: dusk cabinet, 3 caller songbirds, mate songbird, 2 island shard platforms, 6 habitat strips (forest, grass, water, scrub, marsh, rock; 10 m tileable with Start and End sockets), distant flock silhouette, Warbler keeper NPC. The birds and NPC are static, rigs pending. Not Blender items: the UI widgets, audio, and the wind and wave FX. Sheet: shardsong_crossing.png.

## translocation_plan (pythagoras, READY 59018)

11 assets: TRANS01 cabinet with reed topper, ventilated crate, 3 m soft-release pen with gate, planning board (6 years x 4 cohorts), risk gauge (needle plus 95% band), reed marsh 10 m tile, marsh bird at 4 ages (chick, juvenile, subadult, adult), Warden NPC. The birds and Warden are static, rigs pending. Sheet: translocation_plan.png.

## prismchime (unreal-team, READY 59142/59143; 'Blender items' sheet)

6 assets. Name mapping: Cab_Prismchime is built as Prop_Arcade_Cab_Prismchime (shared cabinet sockets, ring-of-bells topper), and NPC_Prismchime_Warden as Mob_Prismchime_Warden (static; shared 8-bone rig pending). Hoop: 1.6 m silver double hoop on a short chain with 8 bell sockets; scale it for the 6- and 10-bell variants. Bell_Dark and Bell_Lit: crystal bell on a rod with 3 pip sockets; Lit is amber emissive. Mallet: prism head. Sheet: prismchime.png.

## gantry_sweep (disk-saver, READY 59154; GS01-GS12)

24 assets: cabinet (GS01), gantry crane (GS02), 4 m quay rail segment (GS03), berth bollard with swappable plate (GS04), trader cog, fishing smack and river barge each with hatch open and closed (GS05), arrival tick board 0-60 (GS06), rail-post slate (GS07), tide flags calm, rush, spread and ragged storm (GS08), verdict lamps sweet, fair and jammed (GS09), crates 0.5, 1 and 2 m (GS10), grease tin (GS11), Railwright Ossian (GS12). The crane and Ossian are static, rigs pending. Plate text is a decal variant. Sheet: gantry_sweep.png.

## buddy_berths (disk-saver, READY 59156; BB01-BB11)

21 assets: cabinet (BB01), 3 m quay unit, 16 tile to 48 m (BB02), chalk-line decal strips for halves, quarters, eighths and sixteenths (BB03), dinghy, ketch, schooner, galleon and great galleon hulls (BB04), ship name pennant with 12 decal variants (BB05), stay hourglass (BB06), Dockmother slate (BB07), turned-away buoy with counter ring (BB08), verdict lanterns snug, fair and crowded (BB09), chalk stick and duster (BB10), Dockmother Imelda (BB11). Imelda is static, rig pending. Sheet: buddy_berths.png.

## golf / Tidelinks Golf (disk-saver, READY 59158; TG01-TG13)

26 assets: cabinet with dune and flag (TG01), tee box with hole plate (TG02), 10 m fairway plus a rough-edge variant (TG03), 20 m green with cup, pin and numbered flag (TG04), 20 m tidal pool band (TG05), OOB stake (TG06), 8 clubs (driver, 3-wood, 5/7/9-iron, wedge, chip, putter) each with a Grip socket, plus an 8-slot rack (TG07), 42.7 mm ball with Trail socket (TG08), 4 m wind sock (TG09), scorecard slate (TG10), verdict pennants masterful, steady and rough (TG11), caddies safe, bold and lay-up (TG12), Greenkeeper Talwyn (TG13). TG08: Prop_Sport_Golf_Ball appears on main only as a data entry in data/sports/throwables-v1.json, with no mesh found, so the ball is built here. All figures are static, rigs pending. Sheet: golf.png.

## fogbell (unreal-team, READY 59509/59510; 'Blender items' sheet)

17 assets: cabinet with bell and lantern marquee, 2.4 m punt with bow lantern, dock lantern lit and unlit, bell gantry, 1.2 m fog bell (origin at the swing pivot; hang at the gantry's BellHang socket), 9-mark tide gauge, and the Harbourmaster and Lantern-bearer, each static plus on the shared Prism segment rig (Rig_* movers, 6 poses). Sheet: fogbell.png.

## emberkiln (unreal-team, READY 60202/60203; 'Blender items' sheet)

13 assets: cabinet, kiln, tongs plain and scorched, coal hopper, tile raw, glazed and cracked, and the Stoker static plus on the shared Prism segment rig (Rig_* movers, 6 poses). Sheet: emberkiln.png.

## hofstadter_hammers (hephaestus, READY 60513; Items sheet)

11 assets: Forge Cabinet slot 36 (anvil marquee, slot plate), slot 36 screen card, the Q hammer (brass) and the Conway hammer (blued twin-face), strike readout and score/streak UI backing panels (runtime UI over SOCKET_UI_Face), and Mob_Forge_Forgemaster static plus on the shared Prism segment rig (also used by crafting_rewards). Sheet: hofstadter_hammers.png.

## sluicegate (unreal-team, READY 61066/61067; 'Blender items' sheet)

18 assets: cabinet with sluice-wheel marquee and water-channel side art, 2.2 m headgate open and closed, 1 m oak board stacked and dropped, sunken 1 x 1 m cistern dry and full (teal), 2.65 m undershot mill wheel idle and turning (spin about X at SOCKET_Axle), earth channel tiles straight, corner, tee and dead end (3 x 3 grid, water slot for runtime wet/next), and the Gatekeeper with crook and board stack, static plus on the shared Prism segment rig. Sheet: sluicegate.png. (game_items.py in this commit also carries the roostcall and crafting_rewards recipes; their kits land in their own PRs.)

## roostcall (unreal-team, READY 59974; 'Blender items' sheet)

18 assets: cabinet with bird-and-whistle marquee, 1.65 m moss-wood roost (2 x 2 cells, open front, 12 Bird_ sockets), Creature_Roostcall_GlimmerBird idle, startled (wings out, emissive flare feathers) and perch (static poses; idle and perch share the perched mesh), 0.15 m bone whistle with Hand socket, low stone yard wall straight, corner and gate, and the Warden static plus on the shared Prism segment rig. Sheet: roostcall.png.

## crafting_rewards batch 1 (hephaestus, READY 62349; items 61000)

8 assets: 1.8 m smelter bench (crucible, mould, shards), ingots Glowsteel, Tidebrass, Galeiron, Umbral alloy and Heartglass (glowsteel and heartglass emissive), scrap bin with scrap, reforge anvil on a stump. The Forgemaster is Mob_Forge_Forgemaster from hofstadter_hammers (same NPC, not rebuilt). Sheet: crafting_rewards.png.

## crafting_rewards batch 2 (hephaestus, READY 62349; items 61072)

10 assets: 1.4 m stone quench trough, 1 m heat gauge with SOFT / TEMPERED / PERFECT / CRACKED bands (runtime heat column), 1.6 m commission board (3 rows), 40 mm Forge Mark token (icon source), hallmark stamp decal plates PLAIN, BRONZE, SILVER, GOLD and PRISM, and the finish tint material set (7 swatches, slot = seal index: none, ember, tide, verdant, gale, umbra, heartglass). Sheet: crafting_rewards_2.png.

## fairpar (pythagoras 60580; docs/mechanics/FAIRPAR01-fair-par.md)

4 assets: 0.3 x 0.12 m Fair Par tier plaques BRONZE, SILVER, GOLD and PERFECT (emissive prism), with a heron relief and 1-4 tier pips. Screw them to the cabinet side under the marquee via SOCKET_CabinetMount, starting with the TRANS01 cabinet (translocation_plan). NONE shows no plaque. Sheet: fairpar.png. (game_items.py also carries the lane_props_r2 and chainmail_weave recipes; their kits land in their own PRs.)

## lane_props_r2 (blender-team lane R2-12, PLAN.md; prism-shard-dev 62389)

9 assets: 1.9 x 1.6 m trophy diorama shelf with 6 Slot_row_col sockets; Fair Par trophy dioramas BRONZE, SILVER, GOLD and PERFECT (1-3 shards, a growing pillar and orb, a halo on PERFECT); Creature_Shardling_Mascot (0.36 m, emissive crystal, Trinket_Hat/Neck/Back/HandR/HandL plus a Shoulder socket); and the Spiritkite kite tail chain Link, Bow and End (0.3 m each, chained by SOCKET_Prev to the previous SOCKET_Next for a UE physics chain). Sheet: lane_props_r2.png.

## chainmail_weave (hephaestus, READY 62846; items 62511 + 62845)

14 assets: armory weave frame with 7 x 7 Ring_row_col sockets (0.2 m pitch); mail rings Empty, Rusted and Link; left and right edge clasps; link budget UI panel; hint glint and hint path glow (VFX placeholders, emissive); difficulty plaques Easy, Normal and Hard; loss banners BLOCKED and OUT OF LINKS. The Forgemaster reuses Mob_Forge_Forgemaster (95e66e111). Sheet: chainmail_weave.png.
