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
