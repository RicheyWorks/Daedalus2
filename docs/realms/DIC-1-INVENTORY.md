# DIC 1: the tabbed inventory, one interaction for every realm

Hub 28570/28573/28574 (2026-10-13): opening the inventory shows tabs in the spirit of ARC Raiders; the *interaction*
is shared by every realm, the *catalog* (tabs, items, slots, actions) and the *theme* (colours, type, panel) are each
realm's own, because each realm is its own game. No shared inventory and no automatic transfer between realms.

## Where it lives
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusInventoryCore.h`: `Catalog` (parses DIC), `Tabs`
  (the behaviour), `Theme`/`Themes()`. Pure C++17; `core-test/inventory_core_test.cpp` proves it (43 checks) without Unreal.
- `Private/SDaedalusInventory.{h,cpp}`: the Slate panel. Draws what `Tabs` says in the catalog's theme; hands `Intent`s
  to the hero. Never changes a count.
- `ADaedalusHero`: `I` opens it (`ToggleInventory`); `InventoryInput` for the harness; `Satchel`/`Worn` hold a realm's
  loot; World Zero's bag is the hero's own tools, armour tiers and mined cubes. `InventoryIntent` is the one place a
  count or a slot changes (EQUIP/UNEQUIP/USE/DROP/PLACE; SPLIT waits on the trade screen).
- `Content/Inventory/<realm>.dic`: world-zero, gallery-city, parcels, bricks, labyrinth.
- `daedalus_play.py` scenario `inventory`: two realms, same commands, different catalogs and themes, counts untouched.

## The controls (every realm)
LB / RB (Q / E) tabs, wrapping; each tab keeps its cursor. D-pad / arrows move on the grid (the theme's column count);
a row wraps end to end, a column stops at the grid's edge. A / Enter opens the item's actions, then picks one.
B / Backspace / I closes the actions, then the panel. Tab badges show how many kinds each tab holds.

## The catalog
```
DIC 1
realm GALLERY-CITY
theme gallery                      Themes(): default gallery parcels bricks labyrinth retro zero
tab ALL                            ALL is every item; the rest are the realm's categories, in order (<= 12)
tab SPRAYS
slot HAND                          equipment slots; EQUIP needs the item's slot to be one
item PAINT_SPRAY SPRAYS HAND EQUIP,INSPECT Paint Spray
detail PAINT_SPRAY Tags the wall you aim at.
```
Actions are words the host understands: EQUIP (UNEQUIP when worn), USE, DROP, SPLIT, PLACE, INSPECT. A realm may add
its own; the panel shows them, the host decides. Refusals are "line N: why".

## Open
- A controller button for the panel: the pad is full (d-pad: view/shoulder/cube/ghost; Menu and View taken). Richey's call.
- Themes are flat colours until Sol's panel materials (neon, kraft, studs, stone, vines) arrive; the `decor` word names them.
- The Java server should read the same .dic for a realm's item rules (Sol); the C++ parser is the reference.
