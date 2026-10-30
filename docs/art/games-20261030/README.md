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
