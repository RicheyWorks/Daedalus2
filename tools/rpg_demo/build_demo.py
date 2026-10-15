# SPDX-License-Identifier: MIT
"""Pack the Prismheart realm into a playable browser demo built only from the real realm outputs.

    python tools/rpg_demo/build_demo.py ART_ROOT OUT_DIR [--sprites DIR]

ART_ROOT is an engines/unreal/art tree (claude-battle-kit, claude-battle-sprites, claude-audio as written by the
tools/blender/rpg_*.py scripts); --sprites can point at a folder holding the battle sprite / party / backdrop _1x
PNGs when they live elsewhere. Writes OUT_DIR/index.html (copied from this folder), atlas images (tiles/sprites/backdrops/spells.png),
data.json (every atlas rectangle by name + the realm's data files merged: town, interiors, demo world map, Cinder Forge,
encounter zones, bestiary, bosses, spells, party, menus, jukebox cues + loop lengths) and audio/ (the jukebox seed MP3s for the cue
vocabulary + the sound-event WAVs the demo emits). Checks before writing: every tile, sprite and sound the data
names exists, and the world map's Cave, Castle and Shrine are reachable on foot from the Town.
Then: python tools/rpg_demo/play_test.py OUT_DIR  (scripted play-through, PASS/FAIL).
"""
import glob
import json
import os
import shutil
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
REALM = "prism"


def J(name):
    with open(os.path.join(REPO, "data", "rpg", name), encoding="utf-8") as f:
        return json.load(f)


class Packer:
    """Shelf packer: add(name, image) then save(path) -> {name: [x, y, w, h]}."""

    def __init__(self, width=1024):
        self.W, self.items = width, []

    def add(self, name, im):
        self.items.append((name, im.convert("RGBA")))

    def save(self, path):
        x = y = shelf = 0
        rects = {}
        for name, im in sorted(self.items, key=lambda t: -t[1].height):
            w, h = im.size
            if x + w > self.W:
                x, y, shelf = 0, y + shelf, 0
            rects[name] = [x, y, w, h]
            x += w
            shelf = max(shelf, h)
        H = y + shelf
        sheet = Image.new("RGBA", (self.W, max(1, H)), (0, 0, 0, 0))
        for name, im in self.items:
            r = rects[name]
            sheet.paste(im, (r[0], r[1]))
        sheet.save(path)
        return rects


def main(argv):
    art = os.path.abspath(argv[0])
    out = os.path.abspath(argv[1])
    spr_dir = os.path.abspath(argv[argv.index("--sprites") + 1]) if "--sprites" in argv else None
    kit = os.path.join(art, "claude-battle-kit", REALM)
    os.makedirs(os.path.join(out, "audio"), exist_ok=True)

    def find(name, *subs):
        for d in ([spr_dir] if spr_dir else []) + [os.path.join(kit, s) for s in subs] + [kit, os.path.join(art, "claude-battle-sprites", REALM)]:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        raise FileNotFoundError(name)

    town, inter, wm, dun = J("town-tiles.json"), J("interiors.json"), J("worldmap-tiles.json"), J("dungeons.json")
    enc, best, boss = J("prism-encounters.json")["zones"], J("prism-bestiary.json"), J("prism-bosses.json")["bosses"]
    spells, party, juke = J("spells.json")["spells"], J("party.json")["party"][REALM], J("jukebox.json")["realms"][REALM]
    types = best.get("types") or best
    types = {t["key"]: t for t in (types if isinstance(types, list) else types.values())}

    # ---- tiles (16x16 frames) -----------------------------------------------------------------------------
    tiles = Packer(1024)
    frames = {}

    def add_tile(key, path):
        im = Image.open(path)
        n = im.width // 16
        frames[key] = n
        for i in range(n):
            tiles.add("%s#%d" % (key, i), im.crop((i * 16, 0, i * 16 + 16, 16)))
    for t in town["tiles"]:
        if t["realm"] == REALM:
            add_tile("town:" + t["tile"], find("Tile_%s_1x.png" % t["tile"], "town"))
    for t in inter["tiles"]:
        if t["realm"] == REALM:
            add_tile("int:" + t["tile"], find("Tile_%s_1x.png" % t["tile"], "interiors"))
    for t in wm["tiles"]:
        if t["realm"] == REALM:
            add_tile("wm:" + t["tile"], find("Tile_%s_1x.png" % t["tile"], "worldmap"))
    forge = next(d for d in dun["dungeons"][REALM] if d["name"] == "Cinder Forge")
    for p in glob.glob(os.path.join(kit, "dungeons", "Tile_%s_*_1x.png" % forge["theme"].title())):
        add_tile("dg:" + os.path.basename(p)[len("Tile_%s_" % forge["theme"].title()):-len("_1x.png")], p)
    tile_rects = tiles.save(os.path.join(out, "tiles.png"))

    # ---- people, enemies, backdrops, spells, ui, title ------------------------------------------------------
    sp = Packer(1024)
    for p in glob.glob(os.path.join(kit, "town", "NPC_*_1x.png")) + glob.glob(os.path.join(kit, "interiors", "NPC_Ruler_1x.png")):
        sp.add(os.path.basename(p)[:-len("_1x.png")], Image.open(p))
    for m in party["members"]:
        sp.add("Party_" + m["job"], Image.open(find("Party_Prism_%s_1x.png" % m["job"])))
    zones = {t["encounter_zone"] for t in wm["tiles"] if t["realm"] == REALM and t["encounter_zone"]}
    zones |= {f["encounters"]["zone"] for f in forge["floors"] if f["encounters"]["zone"]}
    foes = sorted({k for z in zones for fm in enc.get(z, {}).get("formations", []) for k in fm["enemies"]})
    for k in foes:
        sp.add("Foe_" + k, Image.open(find(types[k]["export_name"].replace("Mob_", "Battle_") + "_1x.png")))
    pyre = next(b for b in boss if b["dungeon"] == "Cinder Forge")
    sp.add("Boss_" + pyre["name"], Image.open(find("Battle_Prism_Boss_%s_1x.png" % pyre["name"])))
    for p in glob.glob(os.path.join(kit, "menus", "Icon_*_1x.png")):
        sp.add(os.path.basename(p)[:-len("_1x.png")], Image.open(p))
    for p in glob.glob(os.path.join(kit, "ui", "*_1x.png")):
        sp.add("ui:" + os.path.basename(p)[:-len("_1x.png")], Image.open(p))
    sprite_rects = sp.save(os.path.join(out, "sprites.png"))

    bd = Packer(2048)
    backdrop_zone = {}
    for z in sorted(zones | {"volcano"}):
        cand = [z, z.replace("_deep", ""), "cave" if "cave" in z else "plains"]
        for c in cand:
            try:
                bd.add("bd:" + c, Image.open(find("Backdrop_Prism_%s_1x.png" % c)))
                backdrop_zone[z] = "bd:" + c
                break
            except FileNotFoundError:
                continue
    backdrop_rects = bd.save(os.path.join(out, "backdrops.png"))

    fx = Packer(2048)
    known = set()
    for m in party["members"]:
        known |= set(m["spells"])
    demo_spells = [s for s in spells if s["realm"] == REALM and (s["name"] in known or s["tier"] <= 2)]
    for s in demo_spells:
        fx.add("fx:" + s["name"], Image.open(find("Spell_%s_1x.png" % s["name"].replace(" ", ""), "spells")))
    fx_rects = fx.save(os.path.join(out, "spells.png"))
    shutil.copy(find("Title_1x.png", "title"), os.path.join(out, "title.png"))

    # ---- audio: jukebox seeds for the cues + sound events -------------------------------------------------------
    seeds_dir = os.path.join(art, "claude-audio", "jukebox-seeds")
    cue_files = {}
    seeds = json.load(open(os.path.join(seeds_dir, "realm-cues.json"), encoding="utf-8"))["realms"][REALM]["cues"]
    for cue, s in seeds.items():
        shutil.copy(os.path.join(seeds_dir, s["file"]), os.path.join(out, "audio", s["file"]))
        cue_files[cue] = "audio/" + s["file"]
    ev_files = {}
    for ev, rel in juke["events"].items():
        src = os.path.join(art, "claude-audio", rel)
        dst = os.path.basename(rel)
        shutil.copy(src, os.path.join(out, "audio", dst))
        ev_files[ev] = "audio/" + dst

    # ---- checks ----------------------------------------------------------------------------------------------
    world = wm["demo_maps"][REALM]
    walk = {t["tile"]: t["walkable"] for t in wm["tiles"] if t["realm"] == REALM}

    def find_tile(name):
        return next((x, y) for y, r in enumerate(world) for x, c in enumerate(r) if c == name)
    start = find_tile("Town")
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if 0 <= n[1] < len(world) and 0 <= n[0] < len(world[0]) and n not in seen and (walk.get(world[n[1]][n[0]]) or world[n[1]][n[0]] in ("Cave", "Castle", "Shrine", "Town")):
                seen.add(n)
                q.append(n)
    reach = {k: find_tile(k) in seen for k in ("Cave", "Castle", "Shrine")}
    if not all(reach.values()):
        raise SystemExit("world map: not reachable on foot from the Town: %s" % reach)
    for name, grid in [("town", town["demo_towns"][REALM]["grid"])] + [("int:" + k, v["grid"]) for k, v in inter["interiors"][REALM].items()]:
        for row in grid:
            for c in row:
                if ("town:" + c not in frames) and ("int:" + c not in frames):
                    raise SystemExit("%s uses tile %s with no image" % (name, c))

    data = {
        "realm": "Prismheart", "tile": 16, "screen": [320, 224], "frames": frames,
        "rects": {"tiles": tile_rects, "sprites": sprite_rects, "backdrops": backdrop_rects, "spells": fx_rects},
        "backdrop_for_zone": backdrop_zone,
        "town": town["demo_towns"][REALM], "town_tiles": {t["tile"]: t for t in town["tiles"] if t["realm"] == REALM},
        "interiors": inter["interiors"][REALM], "interior_tiles": {t["tile"]: t for t in inter["tiles"] if t["realm"] == REALM},
        "world": world, "world_tiles": {t["tile"]: t for t in wm["tiles"] if t["realm"] == REALM},
        "dungeon": forge, "dungeon_walkable": dun["walkable"], "dungeon_interact": dun["interact"],
        "zones": {z: enc[z] for z in zones if z in enc},
        "foes": {k: {kk: types[k][kk] for kk in ("name", "level", "hp", "attack", "defence", "speed", "exp", "gold", "element", "behaviour")} for k in foes},
        "boss": pyre, "spells": demo_spells, "party": party,
        "audio": {"cues": cue_files, "events": ev_files,
                  "loops": {c: round(v["loop_end"] / juke.get("sample_rate", 32000), 4) for c, v in juke["cues"].items() if v.get("loop") and c in cue_files}},
        "reach_check": reach,
    }
    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    shutil.copy(os.path.join(HERE, "index.html"), os.path.join(out, "index.html"))
    ctl = os.path.join(REPO, "daedalus-server", "src", "main", "resources", "static", "controllers")   # the shared controller module
    os.makedirs(os.path.join(out, "controllers"), exist_ok=True)
    for f in ("daedalus-pad.js", "controller-bundle.json"):
        shutil.copy(os.path.join(ctl, f), os.path.join(out, "controllers", f))
    st = os.path.join(REPO, "daedalus-server", "src", "main", "resources", "static", "settings")      # the shared settings module
    os.makedirs(os.path.join(out, "settings"), exist_ok=True)
    for f in ("daedalus-settings.js", "settings-schema.json"):
        shutil.copy(os.path.join(st, f), os.path.join(out, "settings", f))
    print("DEMO tiles=%d sprites=%d foes=%d backdrops=%d spells=%d cues=%d events=%d reach=%s" % (
        len(tile_rects), len(sprite_rects), len(foes), len(backdrop_rects), len(fx_rects), len(cue_files), len(ev_files), reach))


if __name__ == "__main__":
    main(sys.argv[1:])
