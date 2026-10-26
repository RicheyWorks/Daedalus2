# ADR-050: Lands, big deep pieces of a shattered world

Status: accepted, 2026-10-12

## Why

Richmond: "each island needs to be as large as the Sandbox lands… cool and able to explore, digging, looking for
resources… what if they buy a land that has super bad-ass resources, you never know. They need to be deep to dig."
The story: the biggest world in the galaxy was hit by a meteor; its pieces float in a bubble like a fishbowl globe,
and people live on them.

## Decision

- **`LandGenerator`** (daedalus-core), selected by radius 32..46 on the existing island API. Islands keep 8..28,
  byte for byte, so every saved world and golden digest is unchanged. A land fits the island claim box (ADR-026):
  up to 92 cubes across and 46 deep, so slots, leases, ownership and deeds work as they are.
- **What a land is**, top down:
  - grass hills (sand at the rim and lake), a lake whose stream falls off the edge as a waterfall, trees,
    blossoms and boulders, and a plank dock where an ark moors;
  - dirt, STONE, then DEEPSTONE below about −16, hanging underneath as an upturned mountain, with two or three
    straight fracture faces where it broke off;
  - winding caves (two 3-D noise fields both near zero);
  - ore veins by depth: COAL_ORE −2..−22, COPPER_ORE −6..−28, IRON_ORE −14..−38, GOLD_ORE −26..−46, and crystal
    geodes on deep cave floors;
  - a glowing HEARTSTONE core at the bottom that holds the piece up. It can't be mined.
- **Richness**, rolled from the seed alone (`LandGenerator.richness`):
  - COMMON (70%);
  - RICH (25%): ×2.2 ore and ×3 gold;
  - LEGENDARY (5%): ×3 ore, plus a meteor crater with a STARMETAL mass under it and starmetal veins below.
  - You never know until you dig (or survey: `LandGenerator.survey`).
- **Block types appended** (ordinals are the save format): DEEPSTONE, HEARTSTONE, COAL_ORE, COPPER_ORE, IRON_ORE,
  GOLD_ORE, STARMETAL. Heartstone and starmetal glow. Colours went into BlockColors and the web realm. The mesh
  fixture was regenerated, and C++ parity holds at 55/55.

## Proven

- `LandGeneratorTest` (5) checks:
  - the same seed gives the same land, and a different seed a different one;
  - the radius dispatch keeps islands and adds lands (29..31 refused);
  - six seeds stay inside the claim box, at least 70 wide, 38+ deep and 3,500+ columns;
  - the strata and ores sit at their depths, the heart is at the bottom, and there is a waterfall;
  - over 400 seeds the richness is about 70/25/5, a legendary land holds starmetal and a common one doesn't.
- daedalus-core verify passes 546 tests, with coverage at 0.95 (ratchet raised to 0.93/0.96) and SpotBugs clean.
- daedalus-server passes 682/682 tests, including the presence wiring that had been failing on main.
- **Live:** the server was restarted with `daedalus-server\server.ps1 -Restart`.
  - Seed 36, which rolls LEGENDARY, was raised into World Zero at slot 4: 213,938 cubes from +21 down to −46.
  - It holds 6,283 coal, 3,540 copper, 1,990 iron, 1,552 gold and 123 starmetal, with 114 crystal clusters.
  - Play loaded it (225 chunks, 126 new). The hero stood on its grass, and the viewport shows the deep cliffs, the
    trees and the glowing waterfall.

## Held

- Surveying in game (a tool that hints what's below).
- Ores dropping as items into the bag with their own colours (they already mine as cubes).
- Ark towing to merge lands.
- The bubble.
- The server's coverage floor: pinned at 0.93, measured 0.82 on main. It is a pre-existing gap and was not
  lowered.
