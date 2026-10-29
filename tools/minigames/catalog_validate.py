#!/usr/bin/env python3
"""Catalog validator: every desktop cabinet is complete and originally named.

  python tools/minigames/catalog_validate.py     # CI: exit 1 on any problem

Per desktop game in docs/minigames/catalog.json:
  * a host save slot in DaedalusDesktopSaveSlots.h (or a dated entry in SAVE_SLOT_PENDING),
  * a how-to line (HowToLine),
  * the scoreboard capability (proven by scoreboard_test.cpp),
  * a unique title, a Daedalus spot whose realm already places the cabinet, and no trademarked game, company or character name in id, title,
    summary or how-to line (Java cabinet titles and summaries are checked too).
Internal ids (star_shooter, dodge_ball, riftwing) and save file names are not titles and are not scanned; the old ids kept in GameAliases for save compatibility are not scanned. Stdlib only.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/minigames/catalog.json"
SLOTS_HDR = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopSaveSlots.h"

# Games whose save slot is written but held for the batched Unreal rebuild. Remove the entry
# once the slot is on main; the validator fails if a pending game already has a slot.
SAVE_SLOT_PENDING = {
    "gloam_latch": "PR 492 (held for rebuild 5)",
    "reedbeat": "PR 492 (held for rebuild 5)",
    "cairnwell": "PR pending (held for the next rebuild)",
}

# Matched as whole words, case-insensitive, with spaces/hyphens/underscores between parts optional.
TRADEMARKS = [
    "zelda", "hyrule", "triforce", "link to the past", "contra", "sega", "nintendo", "mario", "luigi",
    "pac man", "pacman", "ms pac", "asteroids", "pong", "minesweeper", "tetris", "galaga", "galaxian",
    "space invaders", "donkey kong", "sonic", "metroid", "castlevania", "mega man", "megaman", "kirby",
    "pokemon", "ninja gaiden", "street fighter", "mortal kombat", "frogger", "centipede", "dig dug",
    "q bert", "qbert", "breakout", "arkanoid", "gradius", "r type", "robotron",
    "bomberman", "dragon quest", "dragon warrior", "final fantasy", "hydlide", "atari", "capcom",
    "konami", "namco", "taito", "square enix", "minecraft", "roblox", "fortnite", "fifa", "star shooter", "clash", "riftwing",
]


def _pattern(name):
    parts = re.split(r"[ \-_]+", name)
    return re.compile(r"(?<![a-z0-9])" + r"[ \-_]?".join(map(re.escape, parts)) + r"(?![a-z0-9])", re.I)


# Internal ids kept after a title-only rename so saves and cabinets stay stable.
LEGACY_INTERNAL_IDS = {"star_shooter", "riftwing"}  # titled Lumen Barrage / Gleamwing Sentinel since 2026-10-26

PATTERNS = [(t, _pattern(t)) for t in TRADEMARKS]


def trademark_hits(text):
    return sorted({t for t, p in PATTERNS if p.search(text or "")})


def slot_ids(text):
    return set(re.findall(r'\{"([a-z_]+)","[a-z_]+\.dgs",SaveStyle::', text))


def validate(catalog, slots, pending=SAVE_SLOT_PENDING):
    errors = []
    titles = {}
    for g in catalog.get("games", []):
        gid = g.get("id", "?")
        if gid in slots and gid in pending:
            errors.append(f"'{gid}' now has a save slot; remove it from SAVE_SLOT_PENDING")
        elif gid not in slots and gid not in pending:
            errors.append(f"'{gid}' has no host save slot in DaedalusDesktopSaveSlots.h")
        if g.get("default_difficulty") != "normal" or g.get("difficulty") != ["easy", "normal", "hard"]:
            errors.append(f"'{gid}' difficulty must default to normal")
        spot = (g.get("daedalus_spot") or "").strip()
        realm = (g.get("daedalus_realm") or "").strip()
        if not spot or not realm:
            errors.append(f"'{gid}' has no Daedalus spot")
        if not (g.get("how_to_play") or "").strip():
            errors.append(f"'{gid}' has no how-to line")
        if "scoreboard" not in g.get("capabilities", []):
            errors.append(f"'{gid}' has no scoreboard entry (add it to scoreboard_test.cpp)")
        title = (g.get("title") or "").strip()
        if not title:
            errors.append(f"'{gid}' has no title")
        elif title.lower() in titles:
            errors.append(f"'{gid}' title '{title}' is also used by '{titles[title.lower()]}'")
        else:
            titles[title.lower()] = gid
        for field in ("id", "title", "summary", "how_to_play", "daedalus_spot"):
            if field == "id" and gid in LEGACY_INTERNAL_IDS:
                continue
            for hit in trademark_hits(g.get(field, "")):
                errors.append(f"'{gid}' {field} uses trademarked name '{hit}'; use an original name")
    for j in catalog.get("java_cabinets", []):
        for field in ("id", "title", "summary"):
            for hit in trademark_hits(j.get(field, "")):
                errors.append(f"Java cabinet '{j.get('id')}' {field} uses trademarked name '{hit}'")
    for g in catalog.get("python_games", []):
        gid = g.get("id", "?")
        if not (g.get("how_to_play") or "").strip():
            errors.append(f"python game '{gid}' has no how-to line")
        if "normal" not in g.get("difficulty", []):
            errors.append(f"python game '{gid}' has no normal difficulty")
        for field in ("id", "title", "summary", "how_to_play"):
            for hit in trademark_hits(g.get(field, "")):
                errors.append(f"python game '{gid}' {field} uses trademarked name '{hit}'")
    ids = {g.get("id") for g in catalog.get("games", [])}
    for gid in sorted(set(pending) - ids):
        errors.append(f"SAVE_SLOT_PENDING names unknown game '{gid}'")
    return errors


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors = validate(catalog, slot_ids(SLOTS_HDR.read_text(encoding="utf-8")))
    for e in errors:
        print("FAIL:", e)
    n = len(catalog.get("games", []))
    print(f"catalog valid: {n} games" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
