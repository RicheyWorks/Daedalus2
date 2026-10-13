"""Headless ranch production budget check for Hephaestus Island.

Reads layout.json heads + livestock.json product rates + water.json claim_check.
Writes/refreshes livestock.json production_budget and prints a one-line summary.
No Unreal / editor required.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HEPH = ROOT / "data" / "islands" / "hephaestus"
LIVE = HEPH / "livestock.json"
LAYOUT = HEPH / "layout.json"
WATER = HEPH / "water.json"
MIN_DAY = 24 * 60


def main() -> int:
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    water = json.loads(WATER.read_text(encoding="utf-8"))

    heads: dict[str, int] = {}
    for p in layout["placements"]:
        a = p.get("animal")
        if a:
            heads[a] = heads.get(a, 0) + 1

    by_id = {a["id"]: a for a in live["livestock"]}
    products_day: dict[str, float] = {}
    for aid, n in heads.items():
        a = by_id[aid]
        for prod, spec in a.get("products", {}).items():
            every = spec["every_min"]
            chance = spec.get("chance", 1.0)
            rate = n * (MIN_DAY / every) * chance
            products_day[prod] = round(products_day.get(prod, 0.0) + rate, 2)

    wbudget = water.get("budget", {})
    claim = wbudget.get("claim_check", {}).get("both_true", False)
    forgeox_n = heads.get("forgeox", 0)
    bellows_bonus = round(0.15 * forgeox_n, 2)

    failure = {
        "unwatered_1_day": "all products stop",
        "unwatered_3_days": "animal leaves island (cozy: never dies)",
        "unfed_1_day": "all products stop",
        "unfed_3_days": "animal leaves island",
        "trough_empty_forge_shift": "q_forge_temper step 2 fails (RanchTrough_Ash must stay full)",
        "magma_tonic_no_cool_sip": "drinker overheats after magma quench",
    }
    win_meter = {
        "name": "Great Forge Glow",
        "rule": "Glow brightens when water running + pens producing + herb beds watered; tempered win adds dual-quench in pack",
        "signals": {
            "water_running": {
                "check": "HotSpring_Clean flow covers caldera-stress demand",
                "source": "water.json budget.claim_check.both_true",
                "ok": claim,
            },
            "pens_producing": {
                "check": "all 16 heads watered+fed (RanchTrough_Ash / QuenchTrough_Forge + hay/grain/herbs)",
                "heads": sum(heads.values()),
                "species": heads,
            },
            "herb_beds_watered": {
                "check": "12 herb beds get 1 L/day each (Steamreed/Boilbalm need vent or spring that day)",
                "beds": wbudget.get("heads", {}).get("herb_beds", 12),
            },
            "dual_quench_in_pack": {
                "check": "at least one dual-quenched tonic (magma then spring within 10s)",
                "quest": "q_forge_temper step 1",
            },
        },
        "glow_levels": {
            "cold": "0 of water/pens/herbs",
            "ember": "1 of 3 living systems",
            "bright": "2 of 3 living systems",
            "tempered": "all 3 living systems + dual-quench in pack",
        },
    }

    live["production_budget"] = {
        "heads_from_layout": heads,
        "heads_total": sum(heads.values()),
        "products_per_day_full_care": products_day,
        "method": "heads * (1440 / every_min) * chance; assumes watered+fed all day",
        "forgeox_bellows": {
            "heads": forgeox_n,
            "forge_speed_bonus_each": 0.15,
            "forge_speed_bonus_total": bellows_bonus,
            "requires": "watered+fed and near Prop_ForgeBellows_Basalt",
        },
        "slag_grass_fertiliser": {
            "from": "ashgoat",
            "heads": heads.get("ashgoat", 0),
            "effect": "+10% herb bed growth when slag-grass grit applied",
        },
        "water_gate_L_day": {
            "animals_total": wbudget.get("demand_L_day", {}).get("animals_total"),
            "ranch_trough_capacity": 200,
            "note": "RanchTrough_Ash 200 L holds >2 days animal demand at 87.5 L/day",
        },
        "failure_states": failure,
        "win_meter": win_meter,
    }
    LIVE.write_text(json.dumps(live, indent=1) + "\n", encoding="utf-8")

    assert sum(heads.values()) == 16, heads
    assert claim is True, "water claim_check must stay true"
    print(
        f"OK ranch budget: heads={sum(heads.values())} "
        f"egg={products_day.get('egg')} milk={products_day.get('milk')} "
        f"truffle={products_day.get('truffle_mushroom')} wool={products_day.get('wool')} "
        f"honey={products_day.get('honey')} bellows=+{bellows_bonus} water_claim={claim}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
