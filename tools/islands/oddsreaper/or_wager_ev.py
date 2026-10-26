# SPDX-License-Identifier: MIT
"""Headless Wager Herb EV auditor + Storm Parlay Cookbook validator (no Unreal).

Loads data/islands/oddsreaper/herbs.json and checks:
  - every herb storm_ev matches the published formula (storm x1.2, cap 0.95;
    Parlayvine fixed; Stormbloom uses p_eff = 1-(1-p)^2)
  - storm_parlay_cookbook has 6-8 recipes, distinct herb pairs, known ids
  - each recipe's ev_clear / ev_storm / ev_storm_cistern match recomputed EV
    within 0.002 (cistern = further x1.05 during Rain/Storm)

Run:  python tools/islands/oddsreaper/or_wager_ev.py
Exit 0 on PASS, 1 on FAIL. Read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERBS = ROOT / "data" / "islands" / "oddsreaper" / "herbs.json"
STORM = 1.2
CISTERN = 1.05
CAP = 0.95
TOL = 0.002


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def boost(p: float, *, storm: bool, cistern: bool, parlayvine: bool) -> float:
    if parlayvine:
        return p
    if storm:
        p = min(CAP, p * STORM)
    if cistern and storm:
        p = min(CAP, p * CISTERN)
    return p


def p_eff(p: float, *, stormbloom: bool) -> float:
    return 1.0 - (1.0 - p) ** 2 if stormbloom else p


def leg_p(hid: str, p: float, storm: bool, cistern: bool) -> float:
    return p_eff(
        boost(p, storm=storm, cistern=cistern, parlayvine=(hid == "Parlayvine")),
        stormbloom=(hid == "Stormbloom"),
    )


def herb_storm_ev(hid: str, p: float) -> float:
    base = leg_p(hid, p, False, False)
    storm = leg_p(hid, p, True, False)
    return storm / base


def parlay_ev(a: str, pa: float, b: str, pb: float, storm: bool, cistern: bool) -> float:
    clear = leg_p(a, pa, False, False) * leg_p(b, pb, False, False)
    now = leg_p(a, pa, storm, cistern) * leg_p(b, pb, storm, cistern)
    return now / clear


def main() -> int:
    errors: list[str] = []
    doc = load(HERBS)
    herbs = {h["id"]: h for h in doc.get("herbs", [])}
    if len(herbs) != 8:
        errors.append(f"expected 8 herbs, got {len(herbs)}")

    for hid, h in herbs.items():
        p = float(h["p"])
        got = float(h.get("storm_ev", -1))
        want = herb_storm_ev(hid, p)
        if abs(got - want) > TOL:
            errors.append(f"{hid}: storm_ev {got} != computed {want:.4f}")

    book = doc.get("storm_parlay_cookbook") or {}
    recipes = book.get("recipes") or []
    if not 6 <= len(recipes) <= 8:
        errors.append(f"cookbook has {len(recipes)} recipes (want 6-8)")
    if abs(float(book.get("storm_mult", 0)) - STORM) > 1e-9:
        errors.append("cookbook storm_mult must be 1.2")
    if abs(float(book.get("cistern_mult", 0)) - CISTERN) > 1e-9:
        errors.append("cookbook cistern_mult must be 1.05")

    seen: set[str] = set()
    pairs: set[frozenset] = set()
    for r in recipes:
        rid = r.get("id", "?")
        if rid in seen:
            errors.append(f"{rid}: duplicate id")
        seen.add(rid)
        pair = r.get("herbs") or []
        if len(pair) != 2 or len(set(pair)) != 2:
            errors.append(f"{rid}: need 2 distinct herbs")
            continue
        miss = [x for x in pair if x not in herbs]
        if miss:
            errors.append(f"{rid}: unknown herbs {miss}")
            continue
        key = frozenset(pair)
        if key in pairs:
            errors.append(f"{rid}: duplicate herb pair {sorted(pair)}")
        pairs.add(key)
        a, b = pair
        pa, pb = float(herbs[a]["p"]), float(herbs[b]["p"])
        checks = (
            ("ev_clear", False, False),
            ("ev_storm", True, False),
            ("ev_storm_cistern", True, True),
        )
        for field, storm, cistern in checks:
            want = parlay_ev(a, pa, b, pb, storm, cistern)
            got = float(r.get(field, -1))
            if abs(got - want) > TOL:
                errors.append(f"{rid}.{field}: {got} != computed {want:.4f}")

    if errors:
        print("or_wager_ev: FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print(f"or_wager_ev: ALL PASS ({len(herbs)} herbs, {len(recipes)} parlays)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
