# SPDX-License-Identifier: MIT
"""Build the controller bundle every Daedalus client loads.

    python tools/controllers/build_bundle.py

Reads data/controllers/gamecontrollerdb.txt (SDL_GameControllerDB, zlib) and the curated lineup in
curated_source.py, writes data/controllers/curated.json, data/controllers/controller-bundle.json and a copy for the
web clients at daedalus-server/src/main/resources/static/controllers/controller-bundle.json, and prints coverage:
devices per family, which curated models have a community mapping and which rely on the browser's standard
mapping or BIND.

Bundle: families (button names + confirm rule), mame_keys, models (curated, with the USB ids found for them) and
devices: "vvvv:pppp" -> {n: name, f: family, k: model index or -1, m: {W|M|L|A|I: SDL mapping}} where W/M/L/A/I are
Windows, Mac OS X, Linux, Android, iOS.
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import curated_source as C  # noqa: E402

DATA = os.path.join(REPO, "data", "controllers")
STATIC = os.path.join(REPO, "daedalus-server", "src", "main", "resources", "static", "controllers")
PLAT = {"Windows": "W", "Mac OS X": "M", "Linux": "L", "Android": "A", "iOS": "I"}
VENDOR_FAMILY = {"045e": "xbox", "054c": "playstation", "057e": "nintendo", "0ca3": "sega", "3250": "atari",
                 "2c22": "arcade", "0738": "arcade", "16c0": "arcade", "d209": "arcade", "33df": "arcade",
                 "20d6": "xbox", "0e6f": "xbox", "24c6": "xbox", "1532": "xbox", "3537": "xbox", "046d": "xbox",
                 "28de": "xbox", "18d1": "xbox", "1949": "xbox", "146b": "playstation", "0f0d": "xbox"}
NAME_FAMILY = [
    (r"n64|nintendo 64", "n64"), (r"gamecube|\bgc\b|wup-028", "gamecube"), (r"snes|super famicom|super nintendo", "snes"),
    (r"\bnes\b|famicom", "nes"), (r"saturn", "saturn"), (r"sega|genesis|mega drive|megadrive|\bm30\b", "sega"),
    (r"atari|cx40|cx78", "atari"), (r"neo ?geo", "neogeo"), (r"pc engine|turbografx", "pcengine"),
    (r"arcade|fight ?stick|fightstick|fighting (stick|edge|board)|hit ?box|qanba|victrix|panthera|kitsune|atrox|encoder|zero delay|xin-?mo|ultrastik|brook universal", "arcade"),
    (r"switch|joy-?con|pro controller|wii u|nso", "nintendo"),
    (r"ps[2345]|playstation|dualshock|dualsense|sixaxis|raiju", "playstation"),
    (r"xbox|xinput|x-?box|elite|wolverine|kishi|gamesir|8bitdo ultimate|f310|f710", "xbox"),
]


def guid_ids(g):
    """SDL2 GUID -> (bus, vid, pid) when it carries USB ids (bytes 6-7 and 10-11 zero), else None."""
    if len(g) != 32 or not re.fullmatch(r"[0-9a-f]{32}", g):
        return None
    b = bytes.fromhex(g)
    if b[6] or b[7] or b[10] or b[11]:
        return None
    return b[0] | b[1] << 8, "%04x" % (b[4] | b[5] << 8), "%04x" % (b[8] | b[9] << 8)


def main():
    models = [dict(m) for m in C.M]
    rx = [re.compile(m["match"], re.I) for m in models]
    devices, skipped, lines = {}, 0, 0
    for line in open(os.path.join(DATA, "gamecontrollerdb.txt"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines += 1
        parts = line.rstrip(",").split(",")
        guid, name, rest = parts[0].lower(), parts[1], parts[2:]
        plat = next((PLAT.get(p.split(":", 1)[1]) for p in rest if p.startswith("platform:")), None)
        ids = guid_ids(guid)
        if not ids or not plat:
            skipped += 1
            continue
        _, vid, pid = ids
        mapping = ",".join(p for p in rest if not p.startswith(("platform:", "crc:", "hint:", "sdk")) and p)
        key = vid + ":" + pid
        d = devices.setdefault(key, {"n": name, "f": None, "k": -1, "m": {}})
        d["m"].setdefault(plat, mapping)
        if len(name) > len(d["n"]) and plat == "W":
            d["n"] = name
    # curated models <-> devices
    for i, m in enumerate(models):
        found = set()
        if m.get("vid") and m.get("pid"):
            found.add(m["vid"] + ":" + m["pid"])
        for key, d in devices.items():
            if rx[i].search(d["n"]):                       # names are specific enough; vendors change ids across revisions
                found.add(key)
        m["ids"] = sorted(found)
        m["community_map"] = any(k in devices for k in found)
    # each device belongs to the model that matches it best: same vendor first, then the longest name match
    for key, d in devices.items():
        best = None
        for i, m in enumerate(models):
            if key not in m["ids"]:
                continue
            hit = rx[i].search(d["n"])
            score = (100 if m.get("vid") == key[:4] else 0) + (50 if m.get("pid") and m["vid"] + ":" + m["pid"] == key else 0) + (len(hit.group(0)) if hit else 0)
            if best is None or score > best[0]:
                best = (score, i)
        if best:
            d["k"] = best[1]
    for key, d in devices.items():
        n = d["n"].lower()
        if d["k"] >= 0:
            d["f"] = models[d["k"]]["family"]
            if d["f"] in ("playstation", "xbox", "generic") and re.search(NAME_FAMILY[9][0], n):
                d["f"] = "arcade"                          # fight sticks sold as "PS3 / Xbox" still have arcade labels
            continue
        d["f"] = next((f for r, f in NAME_FAMILY if re.search(r, n)), None) or VENDOR_FAMILY.get(key[:4], "generic")
    bundle = {
        "schema": "daedalus.controllers/v1",
        "sources": {"community": "SDL_GameControllerDB c1d5289 (zlib, data/controllers/LICENSE-SDL_GameControllerDB.txt)",
                    "curated": "tools/controllers/curated_source.py"},
        "families": C.FAMILIES, "mame_keys": C.MAME_KEYS, "models": models, "devices": devices,
    }
    with open(os.path.join(DATA, "curated.json"), "w", encoding="utf-8") as f:
        json.dump({"families": C.FAMILIES, "mame_keys": C.MAME_KEYS, "models": C.M}, f, indent=1)
    out = os.path.join(DATA, "controller-bundle.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bundle, f, separators=(",", ":"))
    os.makedirs(STATIC, exist_ok=True)
    shutil.copy(out, os.path.join(STATIC, "controller-bundle.json"))
    explore = os.path.join(REPO, "daedalus-explore", "src", "main", "resources", "controllers")   # GLFW reads the raw file
    os.makedirs(explore, exist_ok=True)
    shutil.copy(os.path.join(DATA, "gamecontrollerdb.txt"), os.path.join(explore, "gamecontrollerdb.txt"))
    fam = {}
    for d in devices.values():
        fam[d["f"]] = fam.get(d["f"], 0) + 1
    makers = {}
    for m in models:
        mk = makers.setdefault(m["maker"], [0, 0])
        mk[0] += 1
        mk[1] += m["community_map"]
    print("SDL lines %d, devices with USB ids %d (%d entries without ids skipped: XInput/hashed GUIDs)" % (lines, len(devices), skipped))
    print("families", dict(sorted(fam.items(), key=lambda t: -t[1])))
    print("curated models %d, with a community mapping %d" % (len(models), sum(m["community_map"] for m in models)))
    print("by maker (models, mapped):", {k: tuple(v) for k, v in sorted(makers.items())})
    print("no community mapping (standard mapping or BIND):", [m["maker"] + " " + m["model"] for m in models if not m["community_map"]])
    print("bundle %.0f KB" % (os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
