# SPDX-License-Identifier: MIT
"""Headless: Hephaestus nft.json card is complete and points at the real Play hero shot.

Read-only. Checks required fields, trait keys, Items == layout.json placement count (119),
hero_image -> hero_unreal_play.png (primary) with hero_r2.png kept only as fallback.
On BLACKBEARD (C:/Users/730ri/projects present) it also checks the PNGs exist and the
primary is a real PNG. Prints PASS/FAIL; exits 1 on any failure.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ISLAND = ROOT / "data" / "islands" / "hephaestus"
NFT = ISLAND / "nft.json"
LAYOUT = ISLAND / "layout.json"
PLAY = "bot-team/shots/hephaestus/hero_unreal_play.png"
FALLBACK = "bot-team/shots/hephaestus/hero_r2.png"
PROJECTS = Path(r"C:\Users\730ri\projects")
REQUIRED = ("name", "sigil", "blurb", "traits", "hero_image")
TRAIT_KEYS = ("Mood", "Water", "Herbs", "Livestock", "Items", "Builder")
EXPECTED_ITEMS = 119
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def main() -> int:
    errs, notes = [], []
    doc = json.loads(NFT.read_text(encoding="utf-8"))
    for k in REQUIRED:
        if not doc.get(k):
            errs.append(f"missing/empty field {k!r}")
    if not str(doc.get("name") or "").startswith("Hephaestus"):
        errs.append(f"name {doc.get('name')!r}")
    traits = doc.get("traits") or {}
    for k in TRAIT_KEYS:
        if k not in traits or traits[k] in ("", None):
            errs.append(f"traits missing {k!r}")
    if "Hephaestus" not in str(traits.get("Builder", "")):
        errs.append(f"Builder {traits.get('Builder')!r}")

    items = traits.get("Items")
    placements = None
    try:
        placements = len(json.loads(LAYOUT.read_text(encoding="utf-8")).get("placements") or [])
    except Exception as e:  # layout unreadable: fall back to the fixed count
        notes.append(f"layout.json unreadable ({e}); using fixed {EXPECTED_ITEMS}")
    if items != EXPECTED_ITEMS:
        errs.append(f"Items expected {EXPECTED_ITEMS}, got {items}")
    if placements is not None and items != placements:
        errs.append(f"Items {items} != layout placements {placements}")

    hero = str(doc.get("hero_image") or "").replace("\\", "/")
    if hero != PLAY:
        errs.append(f"hero_image must be {PLAY}, got {hero!r}")
    if "hero_r2.png" in hero:
        errs.append("hero_image must not use the near-black round-2 SceneCapture as primary")
    fb = str(doc.get("hero_image_fallback") or "").replace("\\", "/")
    if fb != FALLBACK:
        errs.append(f"hero_image_fallback must be {FALLBACK}, got {fb!r}")

    if PROJECTS.is_dir():
        for rel in (PLAY, FALLBACK):
            f = PROJECTS / Path(rel)
            if not f.is_file():
                errs.append(f"missing on disk: {f}")
            elif f.read_bytes()[:8] != PNG_MAGIC:
                errs.append(f"not a PNG: {f}")
            else:
                notes.append(f"on disk: {f.name} {f.stat().st_size} bytes")
    else:
        notes.append("not on BLACKBEARD; skipped PNG existence check")

    for n in notes:
        print(" .", n)
    if errs:
        print("test_heph_nft_card: FAIL")
        for e in errs:
            print(" -", e)
        return 1
    print(f"test_heph_nft_card: ALL PASS (Items {items} == placements {placements}; hero {PLAY})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
