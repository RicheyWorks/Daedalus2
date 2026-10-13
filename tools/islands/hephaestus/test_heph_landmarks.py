# SPDX-License-Identifier: MIT
"""Headless: Hephaestus landmark props from blender-team QUEUE 1360-1366 are in layout.

Read-only. Checks the seven READY landmark assets are present once each with zone+role,
layout.landmarks metadata matches, and nft traits.Items == placement count.
On BLACKBEARD also checks each landmark .glb exists under bot-team/art/glb.
Prints PASS/FAIL; exits 1 on any failure.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ISLAND = ROOT / "data" / "islands" / "hephaestus"
LAYOUT = ISLAND / "layout.json"
NFT = ISLAND / "nft.json"
GLB = Path(r"C:\Users\730ri\projects\bot-team\art\glb")
REQUIRED = (
    "Prop_Asteroid_Core",
    "Prop_Asteroid_Chunk_Small",
    "Prop_Asteroid_Chunk_Large",
    "Prop_Crater_RimRock",
    "Prop_ArkWreck_Hull",
    "Prop_Grok_Monolith",
    "Prop_Grok_SeedPod",
)
ZONE_HINT = {
    "Prop_Asteroid_Core": "meteor_scar",
    "Prop_Asteroid_Chunk_Small": "meteor_scar",
    "Prop_Asteroid_Chunk_Large": "meteor_scar",
    "Prop_Crater_RimRock": "meteor_scar",
    "Prop_ArkWreck_Hull": "ark_drydock",
    "Prop_Grok_Monolith": "caldera_forge",
    "Prop_Grok_SeedPod": "ash_fields",
}


def main() -> int:
    errs, notes = [], []
    lay = json.loads(LAYOUT.read_text(encoding="utf-8"))
    places = lay.get("placements") or []
    by = {}
    for p in places:
        by.setdefault(p.get("asset"), []).append(p)
    for name in REQUIRED:
        rows = by.get(name) or []
        if len(rows) != 1:
            errs.append(f"{name}: expected 1 placement, got {len(rows)}")
            continue
        p = rows[0]
        if p.get("role") != "landmark":
            errs.append(f"{name}: role={p.get('role')!r} (want landmark)")
        want_z = ZONE_HINT[name]
        if p.get("zone") != want_z:
            errs.append(f"{name}: zone={p.get('zone')!r} (want {want_z})")
        notes.append(f"{name} @ {want_z} ({p.get('x')},{p.get('y')},{p.get('z')})")
    meta = lay.get("landmarks") or {}
    assets = meta.get("assets") or []
    if set(assets) != set(REQUIRED):
        errs.append(f"layout.landmarks.assets mismatch: {assets}")
    rows = meta.get("queue_rows") or []
    if rows != list(range(1360, 1367)):
        errs.append(f"queue_rows {rows}")
    nft = json.loads(NFT.read_text(encoding="utf-8"))
    items = (nft.get("traits") or {}).get("Items")
    if items != len(places):
        errs.append(f"nft Items {items} != placements {len(places)}")
    if GLB.is_dir():
        for name in REQUIRED:
            f = GLB / f"{name}.glb"
            if not f.is_file():
                errs.append(f"missing glb: {f}")
            else:
                notes.append(f"glb {name} {f.stat().st_size} bytes")
    else:
        notes.append("glb dir missing; skipped file check")
    for n in notes:
        print(" .", n)
    if errs:
        print("test_heph_landmarks: FAIL")
        for e in errs:
            print(" -", e)
        return 1
    print(f"test_heph_landmarks: ALL PASS ({len(REQUIRED)} landmarks; placements {len(places)}; Items {items})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
