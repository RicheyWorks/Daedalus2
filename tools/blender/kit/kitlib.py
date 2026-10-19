# SPDX-License-Identifier: MIT
"""blender-kit/v1 (blender-team): modular, seeded prop recipes as pure data, built headless by build_kit.py.

A recipe is a list of asset manifests. Each asset has objects (a root named like the asset, plus named child objects for
moving parts, each with a pivot), parts (bevelled boxes, cylinders/cones, lathe profiles; optional rotation in degrees),
1-3 flat material slots per object, SOCKET_<Name> empties, collision children (UCX_ convex boxes/prisms, USP_ spheres;
Unreal names), and LOD1 rules (parts dropped or with fewer segments) for <Asset>_LOD1.glb (ADR-062).
Conventions (docs/production/UNREAL-ONBOARDING.md, Blender section): metres; Blender Z up; origin at the bottom
centre; front = Blender -Y = Unreal +X after the glTF/Interchange swap (buffffff 48487); glTF export +Y up.
States are separate assets <Asset>_<State> with the same pivot and sockets. No node animation on rigid props
(unreal-epic-boss 48497: Unreal drives swing/dip/open).
Everything here is pure Python, so triangle counts and bounds are predicted (and tested) without Blender."""
import hashlib, json, math, random

BOX_TRIS = 44            # a cube with all 12 edges bevelled once (segments=1): 6 + 12 quads + 8 corner tris
BOX_PLAIN_TRIS = 12
BEVEL = 0.12             # bevel offset = BEVEL * the smallest side (same as rifle_recipe.py / build_rifle.py)
SCHEMA = "blender-kit/v1"
AXES = "metres; Blender Z up; origin bottom centre; front = Blender -Y = Unreal +X (glTF/Interchange swap, buffffff 48487); glTF +Y up"


# ------------------------------------------------------------------ parts
def box(name, size, centre, slot, rot=None, bevel=True, lod1=None):
    p = {"name": name, "shape": "box", "size": [round(v, 5) for v in size], "centre": [round(v, 5) for v in centre], "slot": slot, "bevel": bevel}
    if rot: p["rot"] = [round(v, 4) for v in rot]
    if lod1: p["lod1"] = lod1
    return p


def cyl(name, axis, r1, r2, length, centre, slot, segments=12, rot=None, lod1=None):
    """Cylinder or cone along axis 'x'|'y'|'z' (r1 at the - end, r2 at the + end), n-gon caps."""
    p = {"name": name, "shape": "cyl", "axis": axis, "r1": round(r1, 5), "r2": round(r2, 5), "length": round(length, 5),
         "centre": [round(v, 5) for v in centre], "slot": slot, "segments": segments}
    if rot: p["rot"] = [round(v, 4) for v in rot]
    if lod1: p["lod1"] = lod1
    return p


def lathe(name, profile, centre, slot, segments=16, cap_bottom=True, cap_top=True, rot=None, lod1=None):
    """Revolve [(radius, z), ...] (all radius > 0, z ascending or descending) about the local Z axis."""
    p = {"name": name, "shape": "lathe", "profile": [[round(r, 5), round(z, 5)] for r, z in profile], "centre": [round(v, 5) for v in centre],
         "slot": slot, "segments": segments, "caps": [bool(cap_bottom), bool(cap_top)]}
    if rot: p["rot"] = [round(v, 4) for v in rot]
    if lod1: p["lod1"] = lod1
    return p


def part_tris(p, lod=0):
    seg = p.get("segments")
    if lod and p.get("lod1", {}).get("segments"):
        seg = p["lod1"]["segments"]
    if p["shape"] == "box":
        return BOX_TRIS if p.get("bevel", True) else BOX_PLAIN_TRIS
    if p["shape"] == "cyl":
        return 4 * seg - 4
    if p["shape"] == "lathe":
        k = len(p["profile"])
        return 2 * seg * (k - 1) + sum(p["caps"]) * (seg - 2)
    raise ValueError(p["shape"])


def rot_matrix(rot):
    rx, ry, rz = (math.radians(a) for a in rot)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    X = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]; Y = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]; Z = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    mul = lambda A, B: [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(Z, mul(Y, X))          # Blender Euler XYZ: R = Rz * Ry * Rx


def local_verts(p, lod=0):
    """The part's vertices about its own centre, before rotation (exactly what build_kit.py makes)."""
    if p["shape"] == "box":
        a, b, c = (s / 2 for s in p["size"])
        if not p.get("bevel", True):
            return [(x, y, z) for x in (-a, a) for y in (-b, b) for z in (-c, c)]
        o = BEVEL * min(p["size"])
        out = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    out += [(sx * a, sy * (b - o), sz * (c - o)), (sx * (a - o), sy * b, sz * (c - o)), (sx * (a - o), sy * (b - o), sz * c)]
        return out
    seg = p["lod1"]["segments"] if lod and p.get("lod1", {}).get("segments") else p["segments"]
    ring = [(math.cos(2 * math.pi * i / seg), math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    if p["shape"] == "cyl":
        h = p["length"] / 2; out = []
        for r, t in ((p["r1"], -h), (p["r2"], h)):
            for u, v in ring:
                out.append({"x": (t, r * u, r * v), "y": (r * u, t, r * v), "z": (r * u, r * v, t)}[p["axis"]])
        return out
    return [(r * u, r * v, z) for r, z in p["profile"] for u, v in ring]


def part_points(p, lod=0):
    vs = local_verts(p, lod)
    if p.get("rot"):
        M = rot_matrix(p["rot"]); vs = [tuple(sum(M[i][k] * v[k] for k in range(3)) for i in range(3)) for v in vs]
    cx, cy, cz = p["centre"]
    return [(x + cx, y + cy, z + cz) for x, y, z in vs]


def bounds(parts, lod=0):
    pts = [q for p in parts if not (lod and p.get("lod1", {}).get("drop")) for q in part_points(p, lod)]
    lo = [round(min(q[i] for q in pts), 4) for i in range(3)]; hi = [round(max(q[i] for q in pts), 4) for i in range(3)]
    return lo, hi


# ------------------------------------------------------------------ assets
def material(asset, slot, name, hexv, roughness=0.8, metallic=0.0, glow=False):
    return {"slot": slot, "name": "%s_M%d" % (asset, slot), "colour": name, "hex": hexv.upper(), "roughness": roughness, "metallic": metallic, "glow": glow}


def obj(name, parts, parent=None, pivot=(0, 0, 0), role="root"):
    return {"name": name, "parent": parent, "pivot": [round(v, 5) for v in pivot], "role": role, "parts": parts}


def socket(name, location, parent=None, forward=(0, -1, 0)):
    x, y, z = location
    return {"name": name if name.startswith("SOCKET_") else "SOCKET_" + name, "location": [round(v, 5) for v in location], "parent": parent,
            "forward": list(forward), "location_gltf": [round(x, 5), round(z, 5), round(-y, 5) + 0.0]}


def ucx_box(asset, i, size, centre, parent=None):
    return {"name": "UCX_%s_%02d" % (asset, i), "shape": "box", "size": [round(v, 5) for v in size], "centre": [round(v, 5) for v in centre],
            "parent": parent, "tris": 12, "convex": True}


def ucx_prism(asset, i, axis, radius, length, centre, segments=8, parent=None):
    return {"name": "UCX_%s_%02d" % (asset, i), "shape": "cyl", "axis": axis, "r1": radius, "r2": radius, "length": length,
            "centre": [round(v, 5) for v in centre], "segments": segments, "parent": parent, "tris": 4 * segments - 4, "convex": True}


def usp_sphere(asset, i, radius, centre, segments=8, rings=4, parent=None):
    return {"name": "USP_%s_%02d" % (asset, i), "shape": "sphere", "radius": radius, "centre": [round(v, 5) for v in centre],
            "segments": segments, "rings": rings, "parent": parent, "tris": 2 * segments * (rings - 1), "convex": True}


def finish(m):
    """Fill predicted numbers and the recipe hash. m needs asset, objects, materials, sockets, collision, spec."""
    parts = [p for o in m["objects"] for p in o["parts"]]
    lo, hi = bounds(parts)
    lo1, hi1 = bounds(parts, lod=1)
    t0 = sum(part_tris(p) for p in parts)
    t1 = sum(part_tris(p, 1) for p in parts if not p.get("lod1", {}).get("drop"))
    m["predicted"] = {"triangles": t0, "lod1_triangles": t1 if m.get("lod1", True) else None,
                      "lod1_ratio": round(t1 / t0, 3) if m.get("lod1", True) else None,
                      "objects": {o["name"]: sum(part_tris(p) for p in o["parts"]) for o in m["objects"]},
                      "bounds_min": lo, "bounds_max": hi, "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)],
                      "collision_tris": sum(c["tris"] for c in m.get("collision", []))}
    m.setdefault("schema", SCHEMA); m.setdefault("axes", AXES); m.setdefault("status", "STAGED NOT READY")
    m["unreal"] = {"nanite": "on by default on the UE side (unreal-epic-boss)", "sockets": "stock glTF Interchange drops SOCKET_ empties (UEB 48518/48519): "
                   "use the <Asset>.sockets.json sidecar (tools/blender/sockets_sidecar.py); the empties stay in the glb",
                   "collision": "UCX_/USP_ children are kept by stock glTF Interchange (UEB fixture A/B PASS)"}
    m["export"] = {"format": "GLB", "export_yup": True, "export_apply": True, "export_extras": True, "export_animations": False}
    keys = ("objects", "materials", "sockets", "collision")
    m["recipe_sha256"] = hashlib.sha256(json.dumps({k: m.get(k) for k in keys}, sort_keys=True).encode()).hexdigest()
    return m


def rng(seed, asset):
    """Per-asset deterministic RNG: same seed + asset name -> same stream on every machine."""
    return random.Random(int(hashlib.sha256(("%s:%s" % (seed, asset)).encode()).hexdigest()[:16], 16))


def write(assets, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": SCHEMA + "/set", "assets": assets}, f, indent=1); f.write("\n")


def check_asset(m, cap):
    """Generic spec checks used by every recipe's tests: [(name, ok, detail)]."""
    p = m["predicted"]; out = []
    out.append(("%s tris %d <= %d" % (m["asset"], p["triangles"], cap), p["triangles"] <= cap, p["triangles"]))
    out.append(("%s stands on z=0" % m["asset"], abs(p["bounds_min"][2]) < 1e-6, p["bounds_min"][2]))
    out.append(("%s centred x/y (5 cm)" % m["asset"], abs(p["bounds_min"][0] + p["bounds_max"][0]) / 2 < 0.05 and abs(p["bounds_min"][1] + p["bounds_max"][1]) / 2 < 0.05, p["bounds_min"]))
    slots = {o["name"]: sorted({q["slot"] for q in o["parts"]}) for o in m["objects"]}
    out.append(("%s 1-3 slots per object, all defined" % m["asset"], all(1 <= len(s) <= 3 and all(x < len(m["materials"]) for x in s) for s in slots.values()), slots))
    names = [o["name"] for o in m["objects"]] + [s["name"] for s in m["sockets"]] + [c["name"] for c in m.get("collision", [])]
    out.append(("%s unique node names, no spaces" % m["asset"], len(names) == len(set(names)) and not any(" " in n for n in names), ""))
    out.append(("%s root object named like the asset" % m["asset"], m["objects"][0]["name"] == m["asset"] and m["objects"][0]["parent"] is None, ""))
    if p["lod1_triangles"] is not None:
        out.append(("%s LOD1 ~50%% (35-65%%)" % m["asset"], 0.35 <= p["lod1_ratio"] <= 0.65, p["lod1_ratio"]))
    return out
