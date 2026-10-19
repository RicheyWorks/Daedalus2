# CASCADE01 — Trophic Cascade (contest G58)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/TrophicCascade.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/TrophicCascadeTest.java` (10)
Links: BEAVER01 Beaver Waters (the colonies this brings back), ASH01 Ashfall Regrowth (the same valley bands),
VAULT01 / BEE01 (the ark's living cargo).

## Story

When the planet shattered, the arks lifted what they could. The wolves went last. They are hard to load and hard to
love. Down on the regrown fragment the elk came through fine, too fine. With nothing to fear, they stand all
day on the open riverbanks and eat every willow shoot. The banks are bare mud, the beavers have nothing to cut, and
the river runs fast and brown.

Ranger Orrin Vale keeps the ark's last wolf pack. The valley folk would rather shoot more elk. Orrin knows better:
it isn't how many elk there are, it's where they dare to stand.

## Quest `q_trophic_cascade` — "Where the Elk Dare Stand"

1. **Walk the river.** Orrin shows the bare reaches (10 reaches, willow cover 0.15).
2. **Choose the plan.** You have 12 ark wolves (release in any year), 3 fences, and hunters who can cull elk each year.
3. **Run 30 winters.** The outcome:
   - **CASCADE**: mean willow is at least 0.6 and a beaver colony lives. Reward: beaver colonies for BEAVER01 and a willow thicket band on the ecology grid.
   - **PARTIAL**: some reaches recovered (fenced ones, usually).
   - **BROWSED**: the banks stay bare.
   - **CRASHED**: the elk fall below 50 (wolves plus hunters overdo it), or the released wolves die out.

NPC lines (Orrin Vale):
- Start: "Count the elk if you like. Then go and count the willows."
- Cull only: "Fewer elk, same bare banks. They still stand in the river all day."
- Fence: "Willows inside the fence, mud outside. A fence is a pot plant, not a valley."
- Cascade: "Hear that? The beavers are back. The elk keep to the trees now, and the river slows."
- Crash: "Too many guns, or too many teeth. Now the wolves have nothing either."

## Rules (deterministic from the seed and the plan)

- Elk grow logistically: rate 0.3, carrying capacity 800, start at 700. A seeded winter scales the rate by ±30%.
- Wolves kill a·E / (1 + a·h·E) elk each (Holling type II, a 0.02, h 0.05, so at most 20 elk per wolf per year).
  The pack grows by 0.05 wolves per elk killed and loses 35% a year. Territory caps it at 30, and fewer than 1 wolf
  means the pack is gone.
- Hunters remove up to the cull each year.
- Browse pressure on each reach is E·0.0015/reaches/(1 + fear·W), with fear 0.3 (the landscape of fear). Fenced reaches are not browsed.
- Willow grows 0.35·w·(1−w) + 0.02 a year, plus 0.05 where a colony holds the water. A colony eats 0.03 a year.
- Each year one colony settles on the first reach with willow of at least 0.6, up to 4 colonies. A colony leaves when willow drops below 0.2.
- Reach to band: WETLAND under a colony, SCRUB for willow of at least 0.5, MEADOW for 0.2 or more, BARE below that.

## What the tests pin

- With no wolves the banks are browsed bare.
- 6 ark wolves give a CASCADE on seeds 1–5.
- Same wolves without fear: the same elk count, but the banks stay browsed. A 60-elk cull leaves fewer elk and still browsed banks.
- Kills saturate, and the pack settles.
- Fences recover only their own reaches.
- Wolves plus heavy hunting crash the elk.
- Released wolves that starve are a crash.
- Bands follow the willow.
- Determinism, and seed-dependent winters.
- Budgets and refused bad input.

## Host seam

- `TrophicCascade.valley(Settings, seed)`, then `release(year, n)` / `fence(reach)` / `cull(perYear)`, then `run()` → `Report`.
- The host reads `years()` for the timeline: elk, wolves, kills, culled, mean willow, colonies.
- `Report.band(reach)` paints the river cells of the BattlefieldEcology grid. Colony reaches are where BEAVER01 dams start.
- Assets: wolf and elk (reuse the ecology Guild animals), willow thicket (reuse pcg-ecology willow) and a fence segment. See UNREAL-QUEUE / BLENDER-ASKS G58.
