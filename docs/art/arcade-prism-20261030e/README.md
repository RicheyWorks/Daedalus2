# Arcade batch e: 10 reviewed iterations on batch d (NOT READY)
Source `tools/blender/arcade_prism_props_e.py`, kit `data/contest/arcade_prism_e.kit.json`, staged at `bot-team\staging\arcade-prism-20261030e`.
Headless Blender 4.3 (`build_kit.py`, `check_kit.py` all pass), judged by eye on `before_after_sheet.png` (batch d tile left of each new one).
Batch d originals are untouched; every change is a new suffixed asset. Sockets keep batch d names and positions; sidecars pass `engines/sidecar_cpp` (0 problems).

| # | New asset | Tris (d -> new) | Change | Verdict on the sheet |
|---|---|---|---|---|
| 1 | Prop_Arcade_CeilingLightRig_C_v2 | 936 -> 1200 | true hexagon (edges on the apothem at side length) + corner hubs, cans under the hubs | corner gaps gone, cans now on the truss |
| 2 | Prop_Arcade_CeilingLightRig_A_v2 / _B_v2 / _C_v3 | 672/616/1200 -> 848/792/1464 | wider lens + lit colour band per can | light hotspots now read from the 3/4 view |
| 3 | Prop_Arcade_Cab_DancePad_v2 | 620 -> 716 | 2 cm raised arrows, 2.2x larger, P1 magenta / P2 cyan, chrome frame per stage | arrows readable (were invisible) |
| 4 | Prop_Arcade_Cab_Pinball_v2 | 560 -> 760 | side rails, lockdown bar, coin door | front reads as a pinball cab; small |
| 5 | Prop_Arcade_Plush_Pebblepup_v2 | 800 -> 800 | paws tucked under the body | no more floating paws |
| 6 | Prop_Arcade_Plush_Lumenfish_v2 | 292 -> 292 | pectoral fins swept back on the flanks | less "plank" look; modest |
| 7 | Prop_Arcade_HighScoreBoard_v2 | 340 -> 1220 | 5 cm marquee bulbs proud of the panel face (first try sat inside the bezel, fixed) | bulb border clearly visible |
| 8 | Prop_Arcade_TicketCounter_v2 | 256 -> 400 | folded ticket ribbon from ReceiptOut + hood beacon | reads as a redemption machine |
| 9 | Prop_Arcade_PhotoBooth_v2 | 680 -> 1044 | bulb row across the header sign + flash panel (first try too small, enlarged) | header reads as lit |
| 10 | Prop_Arcade_Cab_DancePad_v3 | 716 -> 796 | v2 + lit stage edge strip + front step nosing | stage edge visible; subtle |
