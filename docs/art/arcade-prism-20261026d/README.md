# Arcade batch d (NOT READY)
Source `tools/blender/arcade_prism_props_d.py`, kit `data/contest/arcade_prism_d.kit.json`, staged at `bot-team\staging\arcade-prism-20261026d`.
Headless Blender 4.3 build, checked by eye on `preview_sheet.png` (meshes) and `decals_sheet.png` (carpet + 4 posters, base colour).

| Asset | Tris | Notes |
|---|---|---|
| Prop_Arcade_CeilingLightRig_A | 672 | SOCKET_Hang_0, SOCKET_Hang_1, SOCKET_Light_0, SOCKET_Light_1, SOCKET_Light_2, SOCKET_Light_3 |
| Prop_Arcade_CeilingLightRig_B | 616 | SOCKET_Hang_0, SOCKET_Hang_1, SOCKET_Hang_2, SOCKET_Hang_3, SOCKET_Light_0, SOCKET_Light_1 ... |
| Prop_Arcade_CeilingLightRig_C | 936 | SOCKET_Hang_0, SOCKET_Hang_1, SOCKET_Hang_2, SOCKET_Light_0, SOCKET_Light_1, SOCKET_Light_2 ... |
| Prop_Arcade_TicketCounter | 256 | SOCKET_TicketIn, SOCKET_Display, SOCKET_ReceiptOut, SOCKET_Player1, SOCKET_Floor |
| Prop_Arcade_PhotoBooth | 680 | SOCKET_Seat, SOCKET_Camera, SOCKET_Screen, SOCKET_PhotoSlot, SOCKET_CurtainRail, SOCKET_Entry |
| Prop_Arcade_HighScoreBoard | 340 | SOCKET_Title, SOCKET_Wall, SOCKET_Entry_0, SOCKET_Entry_1, SOCKET_Entry_2, SOCKET_Entry_3 ... |
| Prop_Arcade_Cab_DancePad | 620 | SOCKET_Pad_P1_Up, SOCKET_Pad_P1_Down, SOCKET_Pad_P1_Left, SOCKET_Pad_P1_Right, SOCKET_Player1, SOCKET_Pad_P2_Up ... |
| Prop_Arcade_Cab_Pinball | 560 | SOCKET_FlipperL, SOCKET_FlipperR, SOCKET_Plunger, SOCKET_Backglass, SOCKET_Ball, SOCKET_Player1 ... |
| Prop_Arcade_Plush_Pebblepup | 800 | SOCKET_Shelf, SOCKET_Hand, SOCKET_Grab |
| Prop_Arcade_Plush_Lumenfish | 292 | SOCKET_Shelf, SOCKET_Hand, SOCKET_Grab |
| Decal_Arcade_Poster_StarRun / PrismKnight / CometCup / ShardRacer | - | 60 x 90 cm decalkit posters, no baked words (title = MI/overlay) |
| Decal_Arcade_Carpet_Cosmic | - | 200 x 200 cm, tiles seamlessly |

Rough spots: ceiling rig C ring is a hex truss with small corner gaps; dance-pad arrows are thin slabs (pressed state = MI param); plush are static meshes.
