# SPDX-License-Identifier: MIT
"""Ark Mortar combo resolver (pure Python). combine(['mint','ginger','chamomile']) -> ('ark_tonic', 1.0)."""
import json, os
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "herb_combos.json")
def recipes(path=DATA):
    return json.load(open(path, encoding="utf-8"))["recipes"]
def combine(herbs, path=DATA):
    got = set(h.lower() for h in herbs)
    best = ("herb_mash", 0.0)
    for r in recipes(path):
        need = {i["item"] for i in r["in"]}
        if need == got: return (r["out"][0]["item"], 1.0)
        if len(need & got) >= 2 and best[1] < 0.5: best = (r["out"][0]["item"] + "_lite", 0.5)
    return best
if __name__ == "__main__":
    assert combine(["ginger", "mint", "chamomile"]) == ("ark_tonic", 1.0)
    assert combine(["mint", "ginger", "rock"]) == ("ark_tonic_lite", 0.5)
    assert combine(["rock", "sand", "salt"]) == ("herb_mash", 0.0)
    print("herb_combo ok")
