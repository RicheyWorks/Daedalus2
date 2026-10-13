# SPDX-License-Identifier: MIT
"""Headless: mood.json matches the oddsreaper_storm row in wild_biomes_moods.csv (data-table diagnosis)."""
import csv, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]  # .../Daedalus2/tools/islands/oddsreaper -> Daedalus2
mood = json.loads((REPO / "data" / "islands" / "oddsreaper" / "mood.json").read_text(encoding="utf-8"))
csv_path = REPO / "engines" / "unreal" / "DaedalusLink" / "Content" / "Python" / "wild_biomes_moods.csv"
rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
key0 = list(rows[0].keys())[0]
hit = [r for r in rows if r.get(key0) == "oddsreaper_storm"]
assert hit, "oddsreaper_storm missing from wild_biomes_moods.csv"
row = hit[0]
assert row["DefaultWeather"] == mood["DefaultWeather"] == "Storm"
assert float(row["SunIntensity"]) == float(mood["SunIntensity"])
assert float(row["FogMultiplier"]) == float(mood["FogMultiplier"])
assert float(row["SkyLightIntensity"]) == float(mood["SkyLightIntensity"])
assert mood["id"] == "oddsreaper_storm"
assert mood["mpc_storm"]["Wetness"] == 1.0 and mood["mpc_storm"]["StormPulse"] == 1.0
print("test_mood_row: ALL PASS")
