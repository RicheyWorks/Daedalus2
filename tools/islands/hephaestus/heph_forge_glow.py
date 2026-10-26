"""Headless Great Forge Glow validator for Hephaestus Island.

Loads water.json budget.claim_check, livestock.json production_budget, layout.json,
herbs.json and materials_mpc.json; computes the Great Forge Glow 0-100 score from
signals that are true in data today, simulates the quest-gated dual-quench, checks
the score bands and the MPC_Heph_ForgeSky contract. Prints a JSON summary.
Exit 0 on pass, 1 on fail. Read-only: no file writes, no Unreal / editor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HEPH = ROOT / "data" / "islands" / "hephaestus"

REQUIRED_PARAMS = ["HeatShimmer", "AshFall", "MagmaPulse", "QuenchSteam", "NightForge", "TemperGlow"]
EXPECTED_WEIGHTS = {"water_running": 30, "pens_producing": 30, "herb_beds_watered": 30, "dual_quench_in_pack": 10}
EXPECTED_BANDS = {0: "cold", 1: "ember", 39: "ember", 40: "bright", 69: "bright",
                  70: "near-tempered", 99: "near-tempered", 100: "tempered"}


def load(name: str) -> dict:
    return json.loads((HEPH / name).read_text(encoding="utf-8"))


def level_for(bands: list[dict], score: int) -> str | None:
    hits = [b["level"] for b in bands if b["min"] <= score <= b["max"]]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    errors: list[str] = []
    water = load("water.json")
    live = load("livestock.json")
    layout = load("layout.json")
    herbs = load("herbs.json")
    mpc = load("materials_mpc.json")

    pb = live.get("production_budget", {})
    wm = pb.get("win_meter", {})
    weights = wm.get("score_0_100", {}).get("weights", {})
    bands = wm.get("glow_from_score", [])

    # --- signals from data ---------------------------------------------------
    claim = water.get("budget", {}).get("claim_check", {}).get("both_true") is True

    heads: dict[str, int] = {}
    for p in layout["placements"]:
        a = p.get("animal")
        if a:
            heads[a] = heads.get(a, 0) + 1
    pens_ok = (sum(heads.values()) == 16 and pb.get("heads_total") == 16
               and pb.get("heads_from_layout") == heads)

    herb_beds_layout = sum(1 for p in layout["placements"] if p["asset"].startswith("Item_Herb_"))
    herb_beds_water = water.get("budget", {}).get("heads", {}).get("herb_beds")
    herb_list = herbs.get("herbs", [])
    herbs_with_ev = sum(1 for h in herb_list if "temper_ev" in h)
    beds_ok = herb_beds_layout == 12 and herb_beds_water == 12

    if not claim:
        errors.append("water claim_check.both_true is not true")
    if not pens_ok:
        errors.append(f"pens: layout heads {heads} vs production_budget {pb.get('heads_from_layout')}")
    if not beds_ok:
        errors.append(f"herb beds: layout={herb_beds_layout} water.budget={herb_beds_water} (want 12)")
    if len(herb_list) != 36 or herbs_with_ev != 36:
        errors.append(f"herbs.json: {len(herb_list)} herbs, {herbs_with_ev} with temper_ev (want 36/36)")

    # --- score ---------------------------------------------------------------
    if weights != EXPECTED_WEIGHTS:
        errors.append(f"score weights {weights} != {EXPECTED_WEIGHTS}")
    signals = {"water_running": claim, "pens_producing": pens_ok,
               "herb_beds_watered": beds_ok, "dual_quench_in_pack": False}
    score_now = sum(w for k, w in weights.items() if signals.get(k))
    sim = {**signals, "dual_quench_in_pack": True}
    score_dual = sum(w for k, w in weights.items() if sim.get(k))
    if score_now != 90:
        errors.append(f"headless score {score_now} != 90")
    if score_dual != 100:
        errors.append(f"simulated dual score {score_dual} != 100")
    if wm.get("score_0_100", {}).get("headless_max_without_dual") != 90:
        errors.append("score_0_100.headless_max_without_dual != 90")

    for s in range(0, 101):
        if level_for(bands, s) is None:
            errors.append(f"glow_from_score: score {s} not covered exactly once")
            break
    for s, lvl in EXPECTED_BANDS.items():
        if level_for(bands, s) != lvl:
            errors.append(f"glow_from_score: {s} -> {level_for(bands, s)} (want {lvl})")
    if "tempered_win" not in wm:
        errors.append("win_meter.tempered_win missing")
    for k in ("signals", "glow_levels"):
        if k not in wm:
            errors.append(f"win_meter.{k} missing (legacy contract)")

    # --- MPC contract ---------------------------------------------------------
    if mpc.get("mpc") != "MPC_Heph_ForgeSky":
        errors.append(f"mpc name {mpc.get('mpc')}")
    if mpc.get("applied") is not False:
        errors.append("materials_mpc.applied must be false until an editor turn applies it")
    params = mpc.get("params", {})
    for name in REQUIRED_PARAMS:
        p = params.get(name)
        if not p:
            errors.append(f"MPC param missing: {name}")
            continue
        lo, hi = p.get("range", [None, None])
        if p.get("type") != "scalar" or (lo, hi) != (0.0, 1.0):
            errors.append(f"MPC {name}: want scalar range [0,1], got {p.get('type')} {p.get('range')}")
        elif not lo <= p.get("default", -1) <= hi:
            errors.append(f"MPC {name}: default {p.get('default')} out of range")
        if not p.get("drives"):
            errors.append(f"MPC {name}: drives empty")
    meta = {"mid", "status", "asset", "applies_to", "apply_note"}
    bindings = mpc.get("bindings", [])
    for b in bindings:
        for k in b:
            if k not in meta and k not in params:
                errors.append(f"binding {b.get('mid')}: unknown param {k}")
        if b.get("status") not in ("exists", "planned"):
            errors.append(f"binding {b.get('mid')}: status must be exists|planned")
    temper_now = round(score_now / 100, 2)
    if params.get("TemperGlow", {}).get("headless_now") != temper_now:
        errors.append(f"TemperGlow.headless_now != score/100 ({temper_now})")

    summary = {
        "ok": not errors,
        "signals": signals,
        "score_now": score_now,
        "glow_now": level_for(bands, score_now),
        "score_with_dual_sim": score_dual,
        "glow_with_dual_sim": level_for(bands, score_dual),
        "temper_glow_mpc_now": temper_now,
        "heads": sum(heads.values()),
        "herb_beds": herb_beds_layout,
        "herbs_temper_ev": f"{herbs_with_ev}/{len(herb_list)}",
        "mpc": mpc.get("mpc"),
        "mpc_params": [n for n in REQUIRED_PARAMS if n in params],
        "bindings": {b["mid"]: b.get("status") for b in bindings},
        "errors": errors,
    }
    print(json.dumps(summary, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
