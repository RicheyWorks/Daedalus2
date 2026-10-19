# Prismheart waystones (contest G10, disk-saver)

Old standing stones near each landmark of the Prismheart world map. The lamplighters raised them after the planet
shattered, so travellers between the broken pieces would always have a road home. Walk onto one to wake it; from any
awake stone you can cross to another awake stone for a fare in gold, and the crossing takes half an hour.

| Stone | Near | Lore |
|---|---|---|
| Hearthgate Stone | Town | Set by the first lamplighters so no traveller sleeps outside the walls. |
| Windmere Lodestone | Village | Hums in the same key as the pond's koi when the wind is right. |
| Cinderstep Stone | Cave | Warm to the touch; the Pyre Warden's smoke still clings to it. |
| Aerie Lodestone | Tower | Feathers gather at its foot and never blow away. |
| Sunwell Lodestone | Ruins | Glows faintly at noon, remembering the Sanctum's light. |

## Pieces

- `data/rpg/prism-waystones.json`: the stones (id, permanent save bit, landmark, lore) and the fare
  (`base_gold + gold_per_tile * manhattan tiles`, `minutes`).
- `tools/rpg_demo/waystones.py`: build time. Places each stone on the first free, walkable, foot-reachable tile next to
  its landmark's exit (breadth-first, east/west/south/north), avoiding landmarks and sky caches. The stones follow
  map edits automatically, and a stone that can't be reached fails the build with a reason.
- `tools/rpg_demo/waystones.js`: the rules, with no DOM (browser global `PrismWaystones`, or a Node module): wake,
  destinations (nearest first), travel, and the save string.
- `tools/rpg_demo/index.html`: a small hook. Walking onto a stone wakes it or offers trips. A small pixel stone is
  drawn in code (it glows once awake), so no new art is needed. The inn saves a `ways` string, CONTINUE restores it, and NEW GAME clears it.
  `PRISM_DEMO.waystones()` reports the stones to tests.

## Save string: WAY1

`WAY1.<awake bit mask, lowercase hex, no leading zeros>.<FNV-1a 32 of "WAY1.<mask>", 8 hex>`, for example
`WAY1.7.576471ec`. Each stone owns one bit (0 to 30) forever, so adding stones never breaks old saves, and a build
ignores bits it doesn't know. A string that is too long, malformed, has an unknown version or fails the check loads as
"none awake", and the rest of the save loads normally. Saves from before waystones load with none awake.

## Tests

    node tools/rpg_demo/waystone_core_test.js                  # rules + WAY1, 31 checks
    python -m unittest tools/rpg_demo/waystone_place_test.py   # placement on the real map
    python tools/rpg_demo/build_demo.py ART OUT && python tools/rpg_demo/waystone_test.py OUT   # Playwright, 17 checks
