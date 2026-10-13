# SPDX-License-Identifier: MIT
"""Chapter 7 quest-goal checks without walking chapters 1-6 (evaluates the seed_rain goals directly)."""
import json, random
from succession_depth import colonise
Q = json.load(open("climax_seed_quest.json", encoding="utf-8"))
CH = {c["id"]: c for c in Q["chapters"]}
def goals_met(ch, flags):
    for g in ch["goals"]:
        if g["type"] == "place" and flags.get(g["asset"], 0) < g["n"]: return False
        if g["type"] == "colonised":
            sp = flags.get("islet_species", ())
            if len(sp) < g["n"] or (g.get("need_oak") and "Oak" not in sp): return False
    return True
def test_seed_rain_is_chapter7():
    assert Q["chapters"][6]["id"] == "seed_rain" and Q["chapters"][7]["id"] == "fire_keeper"
def test_wind_alone_fails_without_oak():
    sp = colonise(["Grass", "Fern", "Pine", "Willow", "Oak"], [], 2.0, random.Random(4), wind_aligned=True)
    f = {"Prop_Live_PYT_JayFeeder": 2, "Prop_Veh_PYT_ArkRaft": 1, "islet_species": sp}
    assert "Oak" not in sp and not goals_met(CH["seed_rain"], f)
def test_ark_and_jays_complete_it():
    wins = 0
    for i in range(50):
        sp = colonise(["Grass", "Fern", "Pine", "Willow", "Oak"], [], 2.0, random.Random(i), ark=["Willow", "Pine"], jays=2, wind_aligned=True)
        wins += goals_met(CH["seed_rain"], {"Prop_Live_PYT_JayFeeder": 2, "Prop_Veh_PYT_ArkRaft": 1, "islet_species": sp})
    assert wins >= 30   # 75% expected: jays win once per two tries

