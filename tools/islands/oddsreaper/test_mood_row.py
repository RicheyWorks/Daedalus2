# SPDX-License-Identifier: MIT
"""Headless: mood.json fully matches the oddsreaper_storm row in wild_biomes_moods.csv.

Round-2/3 Play hero daylight bug class: set_mood('oddsreaper_storm') reads this CSV;
a missing or mismatched row falls back to young_meadow daylight. This test gates every
scalar and color channel the director consumes, not just a few floats.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MOOD = REPO / "data" / "islands" / "oddsreaper" / "mood.json"
CSV_PATH = (
    REPO
    / "engines"
    / "unreal"
    / "DaedalusLink"
    / "Content"
    / "Python"
    / "wild_biomes_moods.csv"
)

COLOR_RE = re.compile(
    r"\(R\s*=\s*([-\d.]+)\s*,\s*G\s*=\s*([-\d.]+)\s*,\s*B\s*=\s*([-\d.]+)\s*,\s*A\s*=\s*([-\d.]+)\)",
    re.I,
)


def parse_color(s: str) -> dict:
    m = COLOR_RE.search(s.strip())
    if not m:
        raise AssertionError(f"unparseable color: {s!r}")
    return {
        "R": float(m.group(1)),
        "G": float(m.group(2)),
        "B": float(m.group(3)),
        "A": float(m.group(4)),
    }


def near(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


def main() -> int:
    errors: list[str] = []
    mood = json.loads(MOOD.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    key0 = list(rows[0].keys())[0]
    hit = [r for r in rows if r.get(key0) == "oddsreaper_storm"]
    if not hit:
        print("test_mood_row: FAIL — oddsreaper_storm missing from CSV")
        return 1
    row = hit[0]

    if mood.get("id") != "oddsreaper_storm":
        errors.append(f"id {mood.get('id')!r} != oddsreaper_storm")

    for field in ("DefaultWeather",):
        if row.get(field) != mood.get(field):
            errors.append(f"{field}: csv={row.get(field)!r} mood={mood.get(field)!r}")

    for field in (
        "SunIntensity",
        "SkyLightIntensity",
        "FogMultiplier",
        "FogHeightFalloff",
        "FogStartDistance",
    ):
        if field not in mood:
            errors.append(f"mood.json missing {field}")
            continue
        if not near(row[field], mood[field]):
            errors.append(f"{field}: csv={row[field]!r} mood={mood[field]!r}")

    for field in ("SunColor", "SkyColor", "FogColor"):
        try:
            csv_c = parse_color(row[field])
        except AssertionError as e:
            errors.append(str(e))
            continue
        mj = mood.get(field) or {}
        for ch in ("R", "G", "B", "A"):
            if not near(csv_c[ch], mj.get(ch, 1e9)):
                errors.append(f"{field}.{ch}: csv={csv_c[ch]} mood={mj.get(ch)}")

    mpc = mood.get("mpc_storm") or {}
    for k, want in (
        ("WindStrength", 0.95),
        ("Wetness", 1.0),
        ("StormPulse", 1.0),
        ("NightMask", 0.25),
    ):
        if not near(mpc.get(k, -1), want):
            errors.append(f"mpc_storm.{k}: {mpc.get(k)} != {want}")

    if mood.get("pie_hour") is None or not near(mood["pie_hour"], 18.75, 0.01):
        errors.append(f"pie_hour {mood.get('pie_hour')} != 18.75")

    if errors:
        print("test_mood_row: FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("test_mood_row: ALL PASS (full CSV color+scalar sync + mpc_storm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
