# G132 Meteor Scar Dig

Contest gap G132 (minigame contest 2026-10-19, hephaestus). Source: `daedalus-core/src/main/java/com/daedalus/world/forge/ScarDig.java`, tests in `ScarDigTest` (11).

ISLAND.md beat 6 asks the player to "mine Meteor Scar (starmetal + emberite), rivet at the drydock". Until now the forge lane used starmetal (G19 TemperForge, G24 ArkDrydock) but nothing produced it. Scar Dig is where it comes from.

## Rules

- The scar is a seeded 8 x 8 grid (`ScarDig.plan(seed)`): about 6% starmetal, 8% emberite, 16% slag, 6% steam vents, and the rest rock. The veins glow (Prop_Asteroid_Core has emissive veins), so every cell is visible. The skill is spending water well.
- Strikes to break a cell: slag 1, rock 2, emberite 3, starmetal 4, vent 1.
- Water starts at 60. Every swing costs 2 because the caldera doubles thirst. Breaking a vent scalds for 10 more. A canteen (up to 3; thirst_restore_25 from the island's dual tonics) gives back 25, capped at 60. Swinging at a broken cell or off the scar is wasted but still costs water. Drinking with no canteen is wasted too.
- If the water hits 0, the miner faints. The dig stops and half the haul is dropped.
- Two dual tonics from the island cookbook (mechanics.json) help. **Scar Prospector** (`ore_luck_+10pct`) adds 10% to the starmetal and emberite haul, rounded up. **Drydock Shift** ("a harder swing at Meteor Scar ore") makes every swing strike twice.
- Two starmetal ore smelt to one `starmetal_ingot` (items.json). Emberite goes to the drydock as is.
- Quartermaster Hesper Coalhand weighs the sack at the scar gate: a faint, 3+ ingots ("enough for a plate"), some ore, or only rock and slag.

`ScarDig.run(plan, kit, actions)` is pure, and `Result.encode()` gives one `SCR 1` line. `ScarDig.prospector(plan, kit)` is the reference miner: starmetal first, then emberite, never a vent, and a drink before running dry. Over 100 seeds it never faints or wastes a swing. With both tonics and three canteens it smelts 229 ingots, against 170 with a bare kit.

## Host contract

The host owns the plan and kit, and judges the swing and drink actions it receives. A native C++ core will be its own claim.
