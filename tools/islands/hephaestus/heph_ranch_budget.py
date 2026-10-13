"""Headless ranch production budget check for Hephaestus Island.

Reads layout.json heads + livestock.json product rates + water.json claim_check.
Writes/refreshes livestock.json production_budget (incl. Great Forge Glow 0-100 score)
and prints a one-line summary.
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

# Great Forge Glow 0-100 score (shared with heph_forge_glow.py)
SCORE_WEIGHTS = {
    "water_running": 30,
    "pens_producing": 30,
    "herb_beds_watered": 30,
    "dual_quench_in_pack": 10,
}
GLOW_BANDS = [
    {"min": 0, "max": 0, "level": "cold"},
    {"min": 1, "max": 39, "level": "ember"},
    {"min": 40, "max": 69, "level": "bright"},
    {"min": 70, "max": 99, "level": "near-tempered"},
    {"min": 100, "max": 100, "level": "tempered"},
]


def glow_score(signals: dict[str, bool]) -> int:
    return sum(w for k, w in SCORE_WEIGHTS.items() if signals.get(k))


def glow_level(score: int) -> str:
    for b in GLOW_BANDS:
        if b["min"] <= score <= b["max"]:
            return b["level"]
    raise ValueError(f"score out of range: {score}")


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
        "score_0_100": {
            "weights": dict(SCORE_WEIGHTS),
            "max": sum(SCORE_WEIGHTS.values()),
            "method": "integer sum of weights for signals that are true (0..100)",
            "headless_max_without_dual": sum(SCORE_WEIGHTS.values()) - SCORE_WEIGHTS["dual_quench_in_pack"],
            "note": "dual_quench_in_pack is quest-gated (q_forge_temper step 1); headless max is 90 until a dual-quenched tonic is in pack",
            "validator": "tools/islands/hephaestus/heph_forge_glow.py",
        },
        "glow_from_score": GLOW_BANDS,
        "tempered_win": {
            "rule": "score == 100 sustained for tuning.sustain_ingame_min (data rule; no engine write)",
            "requires": "water_running + pens_producing + herb_beds_watered + dual_quench_in_pack all true",
        },
        "tuning": {
            "sustain_ingame_min": 60,
            "drop_rule": "any signal false -> score drops immediately; tempered_win timer resets",
            "glow_lerp_per_s": 0.1,
            "mpc_param": "MPC_Heph_ForgeSky.TemperGlow = score / 100 (materials_mpc.json)",
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
    # Great Forge Glow score math
    assert sum(SCORE_WEIGHTS.values()) == 100
    base = {"water_running": True, "pens_producing": True, "herb_beds_watered": True}
    assert glow_score({}) == 0 and glow_level(0) == "cold"
    assert glow_score({"water_running": True}) == 30 and glow_level(30) == "ember"
    assert glow_score({"water_running": True, "pens_producing": True}) == 60 and glow_level(60) == "bright"
    assert glow_score(base) == 90 and glow_level(90) == "near-tempered"
    assert glow_score({**base, "dual_quench_in_pack": True}) == 100 and glow_level(100) == "tempered"
    print(
        f"OK ranch budget: heads={sum(heads.values())} "
        f"egg={products_day.get('egg')} milk={products_day.get('milk')} "
        f"truffle={products_day.get('truffle_mushroom')} wool={products_day.get('wool')} "
        f"honey={products_day.get('honey')} bellows=+{bellows_bonus} water_claim={claim} "
        f"glow_score_math=OK(0/30/60/90/100)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
