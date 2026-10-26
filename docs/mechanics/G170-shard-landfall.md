# G170 Shard Landfall (hephaestus, contest 2026-10-19)

The beat after G152 Void Crossing. An ark that made its shard (ARRIVED or ARRIVED_WITH_LOSSES) lands its hold on the
shard's quay, where Quaymistress Tessaly Brund keeps the pens and the market.

- **Pasture (seeded per shard and seed):** forage cap 100..500 dl/day (steps of 50), a price of 4..20 scrip per founding
  pair of each paired kind (emberhen, ashgoat, forgeox, lavaboar, cinderwool), a hive price of 3..6.
- **Whole pairs only.** A pair founds a herd; a lone survivor of a thirsty day in the void cannot. Seed crates always
  plant (5 scrip each). Vent-bee hives land singly. Pets stay with the crew.
- **The quay.** Every head not landed sells for a quarter of its pair price (at least 1); a hive left aboard sells for 1;
  water left sells at 1 scrip per 100 dl; each spare rivet sells for 1.
- **Overgrazing.** Forage is the G24 water rate x heads. Exactly at the cap is fine; one dl over and the new herds are
  worth nothing (OVERGRAZED).
- **Best landing.** Bounded knapsack over pairs and hives (weight = forage, gain = price less what the heads fetch at
  the quay), solved exactly by DP (`ShardLandfall.best`) and checked against brute force on 300 seeded holds.
- **Grades:** THRIVING (= best), SETTLED (>= 75% of best), THIN, OVERGRAZED, NOTHING_ASHORE (breached or never launched).
- **Quest q_shard_landfall:** report_tessaly / replan_landing / sail_again. **SLF 1** one-line encode for the later C++ core.

Code: `daedalus-core/src/main/java/com/daedalus/world/forge/ShardLandfall.java` + `ShardLandfallTest` (9 tests).