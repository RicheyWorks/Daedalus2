# SPDX-License-Identifier: MIT
"""Hephaestus Island hero meshes, procedural glb (no Blender needed, low RAM).
Replaces the 3-box placeholders for the 7 hero assets the turn imports.
Format matches the art queue: 1 node, 1 mesh, 1 primitive per material, Y-up, metres, base at y=0.
    python heph_hero_glb.py OUT_DIR"""
import json, math, os, struct, sys
import numpy as np
import trimesh
from trimesh.creation import box, cylinder, cone, icosphere, annulus
from trimesh.transformations import translation_matrix as T, rotation_matrix as R

MAT = {  # name: (baseColor rgb, metallic, roughness, emissive rgb or None)
    "basalt": ((0.09, 0.085, 0.09), 0.0, 0.92, None),
    "basalt_lt": ((0.20, 0.19, 0.19), 0.0, 0.85, None),
    "iron": ((0.33, 0.32, 0.31), 0.9, 0.45, None),
    "iron_dark": ((0.12, 0.12, 0.13), 0.85, 0.55, None),
    "bronze": ((0.55, 0.36, 0.17), 0.95, 0.35, None),
    "ember": ((1.0, 0.36, 0.06), 0.0, 0.6, (1.0, 0.30, 0.04)),
    "magma": ((1.0, 0.55, 0.12), 0.0, 0.5, (1.0, 0.45, 0.08)),
    "wood": ((0.36, 0.22, 0.12), 0.0, 0.8, None),
    "crystal": ((0.45, 0.75, 1.0), 0.1, 0.15, (0.15, 0.35, 0.6)),
    "crust": ((0.36, 0.30, 0.22), 0.0, 0.9, None),
    "mantle": ((0.62, 0.22, 0.08), 0.0, 0.8, None),
    "core": ((1.0, 0.78, 0.25), 0.2, 0.4, (1.0, 0.62, 0.15)),
    "meteor": ((0.16, 0.15, 0.17), 0.3, 0.8, None),
    "nickel": ((0.70, 0.70, 0.66), 1.0, 0.3, None),
}


class Kit:
    def __init__(s): s.parts = {}
    def add(s, mat, m, *xf):
        m = m.copy()
        for x in xf: m.apply_transform(x)
        s.parts.setdefault(mat, []).append(m)
    def bounds(s):
        allv = np.vstack([p.vertices for ps in s.parts.values() for p in ps]); return allv.min(0), allv.max(0)


def cyl(r, h, z0=0.0, sec=24): return cylinder(radius=r, height=h, sections=sec, transform=T((0, 0, z0 + h / 2)))
def bx(sx, sy, sz, x=0, y=0, z0=0.0): return box(extents=(sx, sy, sz), transform=T((x, y, z0 + sz / 2)))
def rock(r, seed, sub=2, jag=0.25):
    rng = np.random.default_rng(seed); m = icosphere(subdivisions=sub, radius=r)
    n = m.vertices / np.linalg.norm(m.vertices, axis=1, keepdims=True)
    m.vertices = m.vertices + n * rng.uniform(-jag, jag, (len(n), 1)) * r; return m
def shard(r, h, seed):
    rng = np.random.default_rng(seed); m = cone(radius=r, height=h, sections=6)
    m.vertices[:, :2] *= rng.uniform(0.8, 1.2, (len(m.vertices), 1)); return m


def great_forge():
    k = Kit(); sides = 8
    k.add("basalt", cyl(4.2, 1.2, 0, sides))                      # plinth
    k.add("basalt_lt", cyl(3.6, 2.4, 1.2, sides))                 # firebox drum
    k.add("ember", cyl(2.2, 0.3, 3.5, sides))                     # glowing hearth bed
    k.add("magma", annulus(r_min=2.2, r_max=2.6, height=0.12, sections=sides, transform=T((0, 0, 3.66))))
    for i in range(sides):                                        # buttresses + firemouths
        a = 2 * math.pi * i / sides
        k.add("basalt", bx(0.6, 0.9, 3.6), R(a, (0, 0, 1)), T((3.8 * math.cos(a), 3.8 * math.sin(a), 0)))
        if i % 2 == 0:
            k.add("ember", bx(0.12, 0.9, 0.7, z0=1.6), R(a, (0, 0, 1)), T((3.62 * math.cos(a + math.pi / sides), 3.62 * math.sin(a + math.pi / sides), 0)))
    for i in range(4):                                            # iron hood legs
        a = math.pi / 4 + i * math.pi / 2
        k.add("iron_dark", cyl(0.18, 3.4, 3.6, 10), T((2.7 * math.cos(a), 2.7 * math.sin(a), 0)))
    k.add("iron_dark", cone(radius=3.2, height=2.0, sections=sides, transform=T((0, 0, 7.0))))  # hood
    k.add("iron", annulus(r_min=2.9, r_max=3.3, height=0.25, sections=sides, transform=T((0, 0, 7.1))))
    k.add("basalt_lt", cyl(0.9, 4.0, 8.4, sides))                 # chimney stack
    k.add("ember", cyl(0.7, 0.2, 12.4, sides))                    # chimney glow lip
    k.add("bronze", annulus(r_min=0.88, r_max=1.05, height=0.3, sections=sides, transform=T((0, 0, 10.0))))
    k.add("iron", bx(1.6, 0.5, 0.25, 4.6, 0, 1.2)); k.add("iron", bx(0.5, 0.5, 0.9, 5.2, 0, 0.3))  # ash shelf
    return k


def great_anvil():
    k = Kit()
    k.add("basalt", bx(1.4, 1.1, 0.35))                           # stone block
    k.add("iron_dark", bx(1.0, 0.8, 0.25, z0=0.35))               # foot
    k.add("iron_dark", bx(0.5, 0.45, 0.4, z0=0.6))                # waist
    k.add("iron", bx(1.9, 0.6, 0.22, z0=1.0))                     # face (top at 1.22 m)
    h = cone(radius=0.3, height=1.0, sections=16); h.apply_transform(R(math.pi / 2, (0, 1, 0)))
    k.add("iron", h, T((0.95, 0, 1.08)))                           # horn
    k.add("iron", bx(0.35, 0.6, 0.3, -1.1, 0, 0.92))               # heel
    k.add("ember", bx(0.4, 0.25, 0.04, 0.1, 0, 1.22))              # hot billet on the face
    return k


def hammer():
    k = Kit()
    k.add("wood", cyl(0.05, 1.3, 0, 12))
    k.add("iron_dark", bx(0.5, 0.2, 0.22, z0=1.25))
    k.add("bronze", cyl(0.07, 0.12, 1.15, 12))
    k.add("ember", bx(0.04, 0.21, 0.23, 0.26, 0, 1.245))
    return k


def shard_asteroid():
    k = Kit(); rng = np.random.default_rng(7)
    k.add("meteor", rock(0.8, 1, 2, 0.3), T((0, 0, 0.6)))
    for i in range(6):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(0.2, 0.6)
        k.add("nickel", rock(0.18, 10 + i, 1, 0.2), T((d * math.cos(a), d * math.sin(a), 0.6 + rng.uniform(0.2, 0.6))))
    for i in range(5):
        a = rng.uniform(0, 2 * math.pi)
        k.add("crystal", shard(0.12, 0.7, 20 + i), R(rng.uniform(0.2, 0.7), (math.sin(a), -math.cos(a), 0)), T((0.4 * math.cos(a), 0.4 * math.sin(a), 0.9)))
    return k


def shard_planet():
    k = Kit()  # a wedge of the shattered world: crust over mantle over glowing core
    for z0, h, r, m in ((0.0, 0.5, 1.0, "core"), (0.5, 0.6, 1.1, "mantle"), (1.1, 0.35, 1.2, "crust")):
        k.add(m, cylinder(radius=r, height=h, sections=3, transform=T((0, 0, z0 + h / 2))))  # triangular wedge
    k.add("basalt", rock(0.25, 3, 1, 0.3), T((0.3, 0.1, 1.5)))
    for i in range(3): k.add("crystal", shard(0.1, 0.6, 30 + i), T((-0.3 + 0.2 * i, -0.2, 1.4)))
    return k


def rivet_crate():
    k = Kit(); s = 1.1
    k.add("wood", bx(s, s, s))
    for z in (0.05, s - 0.1):
        for y in (-1, 1): k.add("iron_dark", bx(s + 0.04, 0.08, 0.1, 0, y * (s / 2 - 0.04), z))
    rng = np.random.default_rng(5)
    for i in range(8): k.add("nickel", cyl(0.04, 0.03, s, 8), T((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0)))
    return k


def lava_lantern():
    k = Kit()
    k.add("basalt", cyl(0.35, 0.3, 0, 8)); k.add("iron_dark", cyl(0.07, 1.4, 0.3, 10))
    k.add("iron_dark", bx(0.42, 0.42, 0.05, z0=1.7)); k.add("iron_dark", cone(radius=0.32, height=0.3, sections=8, transform=T((0, 0, 2.05))))
    for x, y in ((-1, -1), (-1, 1), (1, -1), (1, 1)): k.add("iron_dark", bx(0.04, 0.04, 0.35, 0.18 * x, 0.18 * y, 1.7))
    k.add("magma", rock(0.15, 9, 1, 0.2), T((0, 0, 1.88)))
    return k


ASSETS = {"Prop_HephaestusForge_Great": great_forge, "Prop_HephaestusAnvil_Great": great_anvil,
          "Tool_HephaestusHammer": hammer, "Item_Shard_Asteroid": shard_asteroid, "Item_Shard_Planet": shard_planet,
          "Prop_ArkRivetCrate": rivet_crate, "Prop_LavaLantern": lava_lantern}
ZUP_TO_YUP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)


def write_glb(name, kit, path):
    bin_, views, accs, prims, mats = bytearray(), [], [], [], []
    def push(arr, target, comp, typ, mm=False):
        while len(bin_) % 4: bin_.append(0)
        off = len(bin_); bin_.extend(arr.tobytes())
        views.append({"buffer": 0, "byteOffset": off, "byteLength": arr.nbytes, "target": target})
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": len(arr), "type": typ}
        if mm: a["min"] = arr.min(0).tolist(); a["max"] = arr.max(0).tolist()
        accs.append(a); return len(accs) - 1
    for i, (mname, ps) in enumerate(kit.parts.items()):
        m = trimesh.util.concatenate(ps); m.apply_transform(ZUP_TO_YUP)
        m.unmerge_vertices()  # flat-shaded facets (in place)
        v = np.asarray(m.vertices, np.float32); n = np.asarray(m.vertex_normals, np.float32); f = np.asarray(m.faces, np.uint32).reshape(-1)
        p = {"attributes": {"POSITION": push(v, 34962, 5126, "VEC3", True), "NORMAL": push(n, 34962, 5126, "VEC3")},
             "indices": push(f, 34963, 5125, "SCALAR"), "material": i}
        prims.append(p)
        c, met, rough, em = MAT[mname]
        mat = {"name": f"{name}_M{i}_{mname}", "pbrMetallicRoughness": {"baseColorFactor": [*c, 1.0], "metallicFactor": met, "roughnessFactor": rough}}
        if em: mat["emissiveFactor"] = list(em)
        mats.append(mat)
    while len(bin_) % 4: bin_.append(0)
    j = {"asset": {"version": "2.0", "generator": "hephaestus heph_hero_glb.py"}, "scene": 0, "scenes": [{"nodes": [0]}],
         "nodes": [{"mesh": 0, "name": name}], "meshes": [{"name": name, "primitives": prims}], "materials": mats,
         "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(bin_)}]}
    js = json.dumps(j, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bytes(bin_)
    open(path, "wb").write(out)
    lo, hi = kit.bounds(); tris = sum(len(p.faces) for ps in kit.parts.values() for p in ps)
    return tris, (hi - lo).round(2).tolist()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."; os.makedirs(out, exist_ok=True)
    for n, fn in ASSETS.items():
        tris, size = write_glb(n, fn(), os.path.join(out, n + ".glb"))
        print(f"{n}: {tris} tris, size_m(x,y,z)={size}")
