# SPDX-License-Identifier: MIT
"""OddsReaper Island layout (deterministic). python make_layout.py > layout.json
Positions in metres, island-local, z up; the Unreal script converts to cm and offsets to the island origin."""
import json, math, random
R = random.Random("oddsreaper-island")
SCALE = 2.0  # contest rule: double the planned island size
P = []
def add(name, x, y, z=0.0, yaw=0.0, s=1.0, zone=""):
    P.append({"asset": name, "x": round(x * SCALE, 2), "y": round(y * SCALE, 2), "z": round(z, 2), "yaw": round(yaw, 1), "scale": s, "zone": zone})
def ring(prefix, n, count, r, z=0.0, zone="", face=True, off=0.0):
    for k in range(count):
        a = 2 * math.pi * k / count + off
        add(f"{prefix}_{k % n:02d}", r * math.cos(a), r * math.sin(a), z, math.degrees(a) + (90 if face else 0), 1.0, zone)

add("Bld_OR_IslandCore_01", 0, 0, -0.25, 0, 1.0, "core")
# Roulette amphitheatre: the heart of the house
add("Prop_OR_Roulette_07", 0, 0, 0, 0, 3.0, "amphitheatre")
ring("Prop_OR_Roulette", 7, 6, 7, zone="amphitheatre")
ring("Prop_OR_FeltTable", 8, 8, 12, zone="amphitheatre")
ring("Prop_OR_OddsBoard", 24, 12, 18, zone="odds_ring")          # boards face the centre
ring("Prop_OR_Lantern", 16, 16, 22, zone="odds_ring", off=0.2)
ring("Prop_OR_SkullTotem", 16, 16, 27, zone="totem_ring")
ring("Bld_OR_Pillar", 16, 16, 31, zone="colonnade")
# Gate on the south side: skull arches and the sigil
for k in range(4): add(f"Bld_OR_SkullArch_{k:02d}", 0, -33 - 4 * k, 0, 0, 1.0, "gate")
for k in range(6): add(f"Prop_OR_Sigil_{k:02d}", (-1) ** k * 4, -36 - 2 * k, 0, 0, 1.5, "gate")
# Oracle spire to the north: crystals around a giant totem
add("Prop_OR_SkullTotem_15", 0, 40, 0, 180, 3.0, "oracle")
for k in range(24): a = R.uniform(0, 6.283); r = R.uniform(3, 9); add(f"Prop_OR_Crystal_{k:02d}", r * math.cos(a), 40 + r * math.sin(a), 0, R.uniform(0, 360), R.uniform(1, 2.5), "oracle")
# Ledger grove NE, herb garden SW, livestock pen SE
for k in range(24): add(f"Prop_OR_LedgerTree_{k:02d}", R.uniform(28, 45), R.uniform(10, 30), 0, R.uniform(0, 360), R.uniform(0.9, 1.4), "ledger_grove")
for k in range(32): add(f"Prop_OR_Herb_{k:02d}", -40 + (k % 8) * 2.2, -20 + (k // 8) * 2.2, 0, R.uniform(0, 360), 1.5, "wager_garden")
for k in range(8): add(f"Item_OR_Herb_{k:02d}", -42 + k * 2.2, -24, 0.9, 0, 1.0, "wager_garden")
for k in range(12): add("Prop_OR_Lantern_00", 35 + 6 * math.cos(k * 0.52), -25 + 6 * math.sin(k * 0.52), 0, 0, 0.6, "pen")  # fence posts
for k in range(4): add(f"Mob_OR_CoinbackGoat_{k:02d}", 33 + R.uniform(-3, 3), -25 + R.uniform(-3, 3), 0, R.uniform(0, 360), 1.0, "pen")
for k in range(4): add(f"Mob_OR_DicebeakHen_{k:02d}", 37 + R.uniform(-2, 2), -23 + R.uniform(-2, 2), 0, R.uniform(0, 360), 1.0, "pen")
for k in range(10): add(f"Item_OR_Food_{k:02d}", 33 + k * 0.4, -30, 0.1, 0, 2.0, "pen")
# Dice-stone cliffs on the rim
for k in range(40): a = 2 * math.pi * k / 40 + R.uniform(-0.05, 0.05); r = R.uniform(52, 60); add(f"Prop_OR_DiceRock_{k:02d}", r * math.cos(a), r * math.sin(a), 0, R.uniform(0, 360), R.uniform(1.5, 3), "cliffs")
# Storm shards hang in the sky above the house
for k in range(12): a = 2 * math.pi * k / 12; add(f"Sky_OR_StormShard_{k:02d}", 25 * math.cos(a), 25 * math.sin(a), R.uniform(30, 55), R.uniform(0, 360), R.uniform(1.5, 3), "storm_crown")
# Table dressing: chips, dice, coins, cards, bags, tonics on the felt tables (r=12 ring)
small = [("Item_OR_Chip", 50), ("Item_OR_Die", 40), ("Item_OR_Coin", 30), ("Item_OR_Cards", 20), ("Item_OR_Tonic", 64)]
k = 0
for prefix, n in small:
    for i in range(n):
        t = k % 8; a = 2 * math.pi * t / 8; k += 1
        add(f"{prefix}_{i:02d}", 12 * math.cos(a) + R.uniform(-0.7, 0.7) / SCALE, 12 * math.sin(a) + R.uniform(-0.4, 0.4) / SCALE, 0.92, R.uniform(0, 360), 1.0, "tables")
for i in range(30): a = R.uniform(0, 6.283); r = R.uniform(14, 16); add(f"Item_OR_MoneyBag_{i:02d}", r * math.cos(a), r * math.sin(a), 0, R.uniform(0, 360), 1.0, "vault_piles")
add("Bld_OR_IslandCore_00", 0, 0, 0, 0, 1.0, "unused")  # keep every item referenced
P[-1]["skip"] = True
print(json.dumps({"island": "OddsReaper", "origin_cm": [400000, -400000, 0], "scale": SCALE, "mood": "oddsreaper_storm",
                  "weather": "Storm", "placements": P}, indent=1))
