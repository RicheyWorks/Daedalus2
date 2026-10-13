"""Headless validator for the Hephaestus Forge Temper dual-quench cookbook.

Loads data/islands/hephaestus/herbs.json (dual_cookbook) and data/herbs/combos.json
(shared essence-pair effects). For every signature recipe it checks:
  - both herb ids exist in herbs.json
  - primary_pair and next_best_pair are distinct and each maps to a combos.json
    effects key (order-insensitive: a+b or b+a)
  - primary_effect / next_best_effect equal that key's effect id
  - both pairs can actually be formed from the two herbs' pooled essences
  - the pair ranking (rank_rule) reproduces primary then next-best
  - quench == "dual", window_s == 10, stations match the Forge Temper stations
Also checks data/islands/hephaestus.json resources.herbs lists every herbs.json id.
Prints PASS/FAIL plus a JSON summary. Exit 0 on pass, 1 on fail.
Read-only: no file writes, no Unreal / editor.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERBS = ROOT / "data" / "islands" / "hephaestus" / "herbs.json"
COMBOS = ROOT / "data" / "herbs" / "combos.json"
MANIFEST = ROOT / "data" / "islands" / "hephaestus.json"

STATIONS = ["Prop_ForgeQuenchTub_Basalt", "HotSpring_Clean"]
WINDOW_S = 10


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def combo_key(effects: dict, pair: str) -> str | None:
    parts = pair.split("+")
    if len(parts) != 2:
        return None
    a, b = parts
    for k in (f"{a}+{b}", f"{b}+{a}"):
        if k in effects:
            return k
    return None


def rank_pairs(herbs: dict, effects: dict, a: str, b: str) -> list[tuple[str, str, int]]:
    """Rank distinct effects from two herbs' pooled essences.

    Every pair of the 4 pooled essence slots that matches a combos key is a candidate.
    Sort: summed potency of the source herbs desc, instant effects first, dur_s desc,
    cross-herb pair before same-herb pair, combos table order. Returns
    [(effect_id, combo_key, potency_sum)] best first, one row per effect id.
    """
    order = list(effects)
    slots = [(e, a) for e in herbs[a]["essences"]] + [(e, b) for e in herbs[b]["essences"]]
    best: dict[str, tuple[tuple, str, int]] = {}
    for (e1, h1), (e2, h2) in itertools.combinations(slots, 2):
        k = combo_key(effects, f"{e1}+{e2}")
        if not k:
            continue
        eff = effects[k]
        pot = herbs[h1]["potency"] + herbs[h2]["potency"]
        sort = (pot, 1 if eff.get("instant") else 0, eff.get("dur_s", 0),
                1 if h1 != h2 else 0, -order.index(k))
        if eff["id"] not in best or sort > best[eff["id"]][0]:
            best[eff["id"]] = (sort, k, pot)
    rows = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
    return [(eid, v[1], v[2]) for eid, v in rows]


def main() -> int:
    errors: list[str] = []
    herbs_doc = load(HERBS)
    effects = load(COMBOS)["effects"]
    manifest = load(MANIFEST)
    herbs = {h["id"]: h for h in herbs_doc.get("herbs", [])}

    book = herbs_doc.get("dual_cookbook")
    recipes = (book or {}).get("recipes", [])
    if not book:
        errors.append("herbs.json missing dual_cookbook")
    if not 6 <= len(recipes) <= 8:
        errors.append(f"dual_cookbook has {len(recipes)} recipes (want 6-8)")

    ids_seen: set[str] = set()
    effects_hit: set[str] = set()
    rows = []
    for r in recipes:
        rid = r.get("id", "?")
        if rid in ids_seen:
            errors.append(f"{rid}: duplicate id")
        ids_seen.add(rid)
        pair_herbs = r.get("herbs", [])
        if len(pair_herbs) != 2 or len(set(pair_herbs)) != 2:
            errors.append(f"{rid}: herbs must be 2 distinct ids")
            continue
        missing = [h for h in pair_herbs if h not in herbs]
        if missing:
            errors.append(f"{rid}: unknown herb ids {missing}")
            continue
        pk = combo_key(effects, r.get("primary_pair", ""))
        nk = combo_key(effects, r.get("next_best_pair", ""))
        if not pk:
            errors.append(f"{rid}: primary_pair {r.get('primary_pair')} not in combos effects")
        if not nk:
            errors.append(f"{rid}: next_best_pair {r.get('next_best_pair')} not in combos effects")
        if pk and nk and pk == nk:
            errors.append(f"{rid}: primary_pair and next_best_pair are the same combo")
        if pk and effects[pk]["id"] != r.get("primary_effect"):
            errors.append(f"{rid}: primary_effect {r.get('primary_effect')} != {effects[pk]['id']}")
        if nk and effects[nk]["id"] != r.get("next_best_effect"):
            errors.append(f"{rid}: next_best_effect {r.get('next_best_effect')} != {effects[nk]['id']}")
        if r.get("quench") != "dual":
            errors.append(f"{rid}: quench must be 'dual'")
        if r.get("window_s") != WINDOW_S:
            errors.append(f"{rid}: window_s must be {WINDOW_S}")
        if r.get("stations") != STATIONS:
            errors.append(f"{rid}: stations must be {STATIONS}")
        ranked = rank_pairs(herbs, effects, *pair_herbs)
        top = [x[0] for x in ranked[:2]]
        want = [r.get("primary_effect"), r.get("next_best_effect")]
        if top != want:
            errors.append(f"{rid}: rank_rule gives {top}, recipe says {want}")
        effects_hit.update(w for w in want if w)
        rows.append({"id": rid, "herbs": pair_herbs, "primary": want[0], "next_best": want[1],
                     "potency": [x[2] for x in ranked[:2]]})

    for need in ("forge_speed_+25pct", "fire_resist", "thirst_restore_25"):
        if need not in effects_hit:
            errors.append(f"cookbook has no recipe landing {need}")
    if not any(sorted(r["herbs"]) == ["Emberleaf", "Forgefern"] for r in rows):
        errors.append("cookbook missing Emberleaf+Forgefern (ISLAND.md example)")

    res_herbs = manifest.get("resources", {}).get("herbs", [])
    if sorted(res_herbs) != sorted(herbs) or len(res_herbs) != len(set(res_herbs)):
        errors.append(f"hephaestus.json resources.herbs has {len(res_herbs)} ids, herbs.json has {len(herbs)}")

    summary = {"recipes": len(recipes), "effects_covered": sorted(effects_hit),
               "resources_herbs": len(res_herbs), "herbs_json": len(herbs), "rows": rows,
               "errors": errors}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print("PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
