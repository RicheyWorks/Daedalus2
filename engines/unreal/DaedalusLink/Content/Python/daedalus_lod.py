# SPDX-License-Identifier: MIT
"""blender-team's BBA 1 LODs, applied the Unreal way (ADR-062 in-game demo; ADR-064 rule 5: far away, fewer faces).

Unreal already switches LODs on the GPU by screen size, so the cheapest correct "swap to _LOD1 at the switch
distance" is: put the _LOD1 glb into the static mesh as LOD 1, and set LOD 1's screen size to the size the mesh has
on screen at the manifest's switch distance. No per-frame code, no extra actors.

    import daedalus_lod
    daedalus_lod.plan(r"...\\catalog.bba", r"...\\glbs", "/Game/BlenderBoss/")    # dry run: what would change
    daedalus_lod.apply(r"...\\catalog.bba", r"...\\glbs", "/Game/BlenderBoss/")   # do it (blender-team's OK first)

Only meshes under the given folder are touched, only ones whose name is a manifest id, and only LOD 1.
The parser is a line-for-line port of DaedalusAssetLodCore.h; test_daedalus_lod.py replays asset_lod_parity.txt.
"""
import math
import os

MAX_ASSETS = 200000
MAX_FACES = 10000000
MAX_CM = 100000000
MAX_LINE = 512


class Asset:
    __slots__ = ("id", "lod0", "lod1", "radius", "switch")

    def __init__(self, id_, lod0, lod1, radius, switch):
        self.id, self.lod0, self.lod1, self.radius, self.switch = id_, lod0, lod1, radius, switch


def _token(s):
    return 0 < len(s) <= 96 and all(c.isascii() and (c.isalnum() or c in "_-.") for c in s)


def _int(s, lo, hi):
    if not s or len(s) > 12 or any(c < "0" or c > "9" for c in s) or (len(s) > 1 and s[0] == "0"):
        return None
    v = int(s)
    return v if lo <= v <= hi else None


def parse(text):
    """(assets, None) or (None, "line N: why"), exactly as the C++ Parse."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    head, assets = False, []
    for i, line in enumerate(lines):
        n = i + 1
        if line.endswith("\r"):
            line = line[:-1]
        if len(line.encode("utf-8")) > MAX_LINE:
            return None, "line %d: line too long" % n
        if not line or line[0] == "#":
            continue
        if "\t" in line:
            return None, "line %d: tab" % n
        w = [x for x in line.split(" ") if x]
        if not head:
            if len(w) != 2 or w[0] != "BBA":
                return None, "line %d: expected 'BBA 1'" % n
            if w[1] != "1":
                return None, "line %d: unsupported version %s" % (n, w[1])
            head = True
            continue
        if w[0] != "asset":
            return None, "line %d: unknown record %s" % (n, w[0])
        if len(w) != 10 or w[2] != "lod0" or w[4] != "lod1" or w[6] != "radius" or w[8] != "switch":
            return None, "line %d: expected 'asset <id> lod0 <n> lod1 <n|-> radius <cm> switch <cm>'" % n
        if not _token(w[1]):
            return None, "line %d: bad asset id" % n
        lod0 = _int(w[3], 1, MAX_FACES)
        if lod0 is None:
            return None, "line %d: bad lod0" % n
        lod1 = -1
        if w[5] != "-":
            lod1 = _int(w[5], 1, MAX_FACES)
            if lod1 is None:
                return None, "line %d: bad lod1" % n
        if lod1 > lod0:
            return None, "line %d: lod1 has more faces than lod0" % n
        radius = _int(w[7], 1, MAX_CM)
        if radius is None:
            return None, "line %d: bad radius" % n
        switch = _int(w[9], 0, MAX_CM)
        if switch is None:
            return None, "line %d: bad switch" % n
        assets.append(Asset(w[1], lod0, lod1, radius, switch))
        if len(assets) > MAX_ASSETS:
            return None, "line %d: too many assets" % n
    if not head:
        return None, "line %d: empty" % (len(lines) + 1)
    ids = sorted(a.id.encode() for a in assets)
    for a, b in zip(ids, ids[1:]):
        if a == b:
            return None, "duplicate asset " + a.decode()
    return assets, None


def write(assets):
    out = ["BBA 1\n"]
    for a in sorted(assets, key=lambda x: x.id.encode()):
        out.append("asset %s lod0 %d lod1 %s radius %d switch %d\n" % (
            a.id, a.lod0, "-" if a.lod1 < 0 else str(a.lod1), a.radius, a.switch))
    return "".join(out)


def select(a, distance_cm):
    return 1 if a.lod1 >= 0 and distance_cm >= a.switch else 0


def screen_size(radius_cm, distance_cm, hfov_deg=90.0, aspect=16.0 / 9.0):
    """Unreal's ComputeBoundsScreenSize for a sphere of radius_cm at distance_cm: 2 * max(P00, P11) / 2 * r / d,
    with P00 = 1 / tan(hfov / 2) and P11 = aspect * P00 (Unreal keeps the horizontal FOV fixed). Clamped to 0..1."""
    if distance_cm <= 0:
        return 1.0
    p00 = 1.0 / math.tan(math.radians(hfov_deg) / 2.0)
    multiple = max(0.5 * p00, 0.5 * p00 * aspect)
    return max(0.0, min(1.0, 2.0 * multiple * radius_cm / max(distance_cm, 1.0)))


def actions(assets, glb_dir, existing):
    """What to do per mesh. existing: {asset id: (package path, lod count)} of meshes found under the folder."""
    out = []
    for a in sorted(assets, key=lambda x: x.id):
        if a.id not in existing:
            continue
        pkg, lods = existing[a.id]
        if a.lod1 < 0:
            out.append({"id": a.id, "mesh": pkg, "do": "skip", "why": "no LOD1 in the manifest"})
            continue
        glb = os.path.join(glb_dir, a.id + "_LOD1.glb")
        size = round(screen_size(a.radius, a.switch), 4)
        if lods >= 2:
            out.append({"id": a.id, "mesh": pkg, "do": "screen size", "lod1_screen_size": size})
        elif os.path.exists(glb):
            out.append({"id": a.id, "mesh": pkg, "do": "import LOD1 + screen size", "glb": glb, "lod1_screen_size": size})
        else:
            out.append({"id": a.id, "mesh": pkg, "do": "skip", "why": "no " + os.path.basename(glb)})
    return out


def _existing(folder):
    import unreal
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh")],
                          package_paths=[folder.rstrip("/")], recursive_paths=True)
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    found = {}
    for a in ar.get_assets(flt):
        name = str(a.asset_name)
        mesh = a.get_asset()
        found[name] = (str(a.package_name), sub.get_lod_count(mesh) if mesh else 0)
    return found


def plan(bba_path, glb_dir, folder):
    with open(bba_path, encoding="utf-8") as f:
        assets, err = parse(f.read())
    if err:
        return {"error": err}
    acts = actions(assets, glb_dir, _existing(folder))
    return {"assets": len(assets), "meshes": len(acts), "actions": acts[:200],
            "counts": {k: sum(1 for x in acts if x["do"] == k) for k in {x["do"] for x in acts}}}


def apply(bba_path, glb_dir, folder):
    """Imports LOD1 where missing and sets LOD1's screen size. Saves each changed mesh. Reports every outcome."""
    import unreal
    with open(bba_path, encoding="utf-8") as f:
        assets, err = parse(f.read())
    if err:
        return {"error": err}
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    done = []
    for act in actions(assets, glb_dir, _existing(folder)):
        if act["do"] == "skip":
            continue
        mesh = unreal.load_asset(act["mesh"])
        try:
            if act["do"].startswith("import"):
                got = sub.import_lod(mesh, 1, act["glb"])
                if got != 1:
                    done.append(dict(act, ok=False, why="import_lod returned %s" % got))
                    continue
            mesh.set_editor_property("auto_compute_lod_screen_size", False)
            if hasattr(sub, "set_lod_screen_sizes"):
                sub.set_lod_screen_sizes(mesh, [1.0, act["lod1_screen_size"]])
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)
            done.append(dict(act, ok=True))
        except Exception as e:  # one bad mesh is reported, the rest carry on
            done.append(dict(act, ok=False, why=repr(e)[:200]))
    return {"changed": sum(1 for d in done if d.get("ok")), "failed": [d for d in done if not d.get("ok")][:50]}
