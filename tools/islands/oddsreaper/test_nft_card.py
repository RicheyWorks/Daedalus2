# SPDX-License-Identifier: MIT
"""Headless: OddsReaper nft.json points at the real Play hero shot (not the black editor capture)."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NFT = ROOT / "data" / "islands" / "oddsreaper" / "nft.json"
PLAY = "bot-team/shots/oddsreaper/hero_unreal_play.png"
EDITOR_BAD = "hero_unreal_editor.png"

def main() -> int:
    doc = json.loads(NFT.read_text(encoding="utf-8"))
    errs = []
    hero = str(doc.get("hero_image") or "")
    if PLAY not in hero.replace("\\", "/"):
        errs.append(f"hero_image must reference {PLAY}, got {hero!r}")
    if EDITOR_BAD in hero:
        errs.append("hero_image must not use the black editor SceneCapture")
    items = (doc.get("traits") or {}).get("Items")
    if items != 591:
        errs.append(f"Items expected 591, got {items}")
    if not str(doc.get("name") or "").startswith("OddsReaper"):
        errs.append(f"name {doc.get('name')!r}")
    if errs:
        print("test_nft_card: FAIL")
        for e in errs:
            print(" -", e)
        return 1
    print("test_nft_card: ALL PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
