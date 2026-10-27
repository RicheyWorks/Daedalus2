# SPDX-License-Identifier: MIT
"""Prismheart arcade props (blender-team, Richey order relayed by buffffff 2026-10-26): shard facets, the heart sphere and
arcade cabinet cabs for the minigame arcade (data/minigames/realm-cabinets.json, prismheart_realm arcade_plaza). Original names.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/arcade_prism_props.py -- OUT_DIR [Name,Name,...]

Per asset: OUT/<Name>/<Name>.glb (mesh + UCX_ box + SOCKET_ empties), <Name>.sockets.json (sockets_sidecar schema, UE cm),
<Name>.json (stats). OUT/arcade_prism_manifest.json lists every asset with its sockets and the Daedalus hook.
Daedalus hook: cabinets snap to a realm-cabinets.json slot by SOCKET_Floor (pivot = floor centre, Blender front -Y, place
with yaw -90 like every team glb); minigame UI binds to SOCKET_Screen / SOCKET_Marquee; the heart sphere seats six facets on
SOCKET_Facet_0..5 (facet SOCKET_Seat); every facet's SOCKET_Glow is the VFX/light anchor. Reuses realm_prism_props voxel helpers.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realm_prism_props as RP  # noqa: E402

C, box, disc, gem, PAL = RP.C, RP.box, RP.disc, RP.gem, RP.PAL

FACET_COL = {  # element: (body, sparkle) - same six elements as Prop_Prism_Shard_*
    "Fire": ((1.0, .42, .18), (1.0, .85, .40)), "Tide": ((.20, .55, 1.0), (.70, .90, 1.0)),
    "Gale": ((.45, .95, .55), (.85, 1.0, .85)), "Stone": ((.75, .55, .35), (.95, .85, .65)),
    "Light": ((1.0, .95, .60), (1.0, 1.0, .95)), "Shade": ((.45, .25, .70), (.80, .60, 1.0)),
}
CAB_DARK, CAB_TRIM = C((.12, .10, .18)), C((.35, .30, .55))
SCREEN, SCREEN_RIM = C((.05, .08, .12)), C((.20, .22, .26))
BTN_R, BTN_B, BTN_Y = C((.90, .20, .20)), C((.20, .45, .95)), C((.98, .85, .20))
CAB_STYLE = {  # name: (body colour, trim/marquee colour)
    "Prismheart": (C((.20, .16, .36)), RP.PRISM), "Shardring": (C((.10, .22, .30)), RP.PRISM2),
    "Waystone": (C((.30, .28, .26)), RP.GLOW), "Cocktail": (C((.16, .10, .14)), RP.GOLD),
}

CATALOG = {}  # name -> (kind, voxel cm)
for e in FACET_COL:
    CATALOG["Prop_Prism_ShardFacet_" + e] = ("facet", 5.0)
CATALOG["Prop_Prism_HeartSphere"] = ("sphere", 5.0)
for s in CAB_STYLE:
    CATALOG["Prop_Arcade_Cab_" + s] = ("cabinet", 5.0)


def facet(e):
    """Faceted shard: a tall octahedral crystal with a smaller side crystal; seat at z=0."""
    c1, c2 = C(FACET_COL[e][0]), C(FACET_COL[e][1])
    o = []
    gem(o, 0, 0, 0, 3, 12, c1, c2)
    gem(o, 2, 1, 0, 1, 6, c2, c1)
    socks = {"SOCKET_Seat": ((0, 0, 0), None), "SOCKET_Glow": ((0, 0, 9), None)}
    return o, socks


def sphere():
    """Prism heart: faceted voxel sphere (r=10 vox, ~1 m) on a stone collar; six facet seats round the equator."""
    o = []
    R, zc = 10, 13
    for x in range(-R, R + 1):
        for y in range(-R, R + 1):
            for z in range(-R, R + 1):
                d = x * x + y * y + z * z
                if R * R - 2 * R <= d <= R * R:
                    c = RP.PRISM2 if (abs(x) + abs(y) + abs(z)) % 5 == 0 else RP.PRISM
                    o.append((x, y, zc + z, c))
    disc(o, 0, 0, 0, 6, RP.STONE_D, 2)
    disc(o, 0, 0, 2, 4, RP.STONE, 2)
    socks = {"SOCKET_Base": ((0, 0, 0), None), "SOCKET_Core": ((0, 0, zc), None)}
    for i in range(6):
        a = i * math.pi / 3
        socks["SOCKET_Facet_%d" % i] = ((round(R * math.cos(a), 2), round(R * math.sin(a), 2), zc), None)
    return o, socks


def cabinet(s):
    """Arcade cab, 5 cm voxels: 0.7 m wide, 0.8 m deep, 1.8 m tall upright (Cocktail: low table cab). Front = -Y."""
    body, trim = CAB_STYLE[s]
    o = []
    if s == "Cocktail":
        box(o, -8, -8, 0, 16, 16, 14, body)
        box(o, -9, -9, 14, 18, 18, 1, trim)
        box(o, -6, -6, 15, 12, 12, 1, SCREEN)
        for x, c in ((-3, BTN_R), (0, BTN_B), (3, BTN_Y)):
            box(o, x, -9, 15, 1, 1, 1, c)
        return o, {"SOCKET_Floor": ((0, 0, 0), None), "SOCKET_Screen": ((0, 0, 16), None),
                   "SOCKET_Player1": ((0, -10, 15), None), "SOCKET_Player2": ((0, 10, 15), None),
                   "SOCKET_CoinSlot": ((0, -9, 7), None)}
    box(o, -7, -8, 0, 14, 16, 2, CAB_DARK)            # plinth
    box(o, -7, -6, 2, 14, 14, 16, body)               # lower body
    box(o, -7, -10, 16, 14, 6, 2, trim)               # control deck
    for x, c in ((-4, BTN_R), (-1, BTN_B), (2, BTN_Y), (4, BTN_R)):
        box(o, x, -9, 18, 1, 1, 1, c)
    box(o, -1 - 4, -8, 18, 2, 2, 2, CAB_DARK)        # stick
    box(o, -7, -4, 18, 14, 12, 14, body)              # upper body
    box(o, -6, -5, 19, 12, 1, 11, SCREEN_RIM)
    box(o, -5, -5, 20, 10, 1, 9, SCREEN)
    box(o, -7, -6, 32, 14, 14, 4, trim)               # marquee
    box(o, -1, -7, 6, 2, 1, 2, RP.GOLD)               # coin door
    gem(o, 0, 0, 36, 2, 5, RP.PRISM, RP.PRISM2)       # crest
    return o, {"SOCKET_Floor": ((0, 0, 0), None), "SOCKET_Screen": ((0, -5.5, 24.5), None),
               "SOCKET_Marquee": ((0, -6.5, 34), None), "SOCKET_Player1": ((0, -12, 0), None),
               "SOCKET_CoinSlot": ((0, -7.5, 7), None)}


def plan(name):
    kind, _ = CATALOG[name]
    short = name.rsplit("_", 1)[1]
    return {"facet": facet, "cabinet": cabinet}[kind](short) if kind != "sphere" else sphere()


def _ue(v):  # sockets_sidecar mapping: UE = 100 * (x_b, -y_b, z_b)
    return [round(v[0] * 100.0, 3) + 0.0, round(-v[1] * 100.0, 3) + 0.0, round(v[2] * 100.0, 3) + 0.0]


def build(name, out_root):
    import bpy
    import voxel_island as V
    kind, cm = CATALOG[name]
    vox, socks = plan(name)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    unit = cm / 100.0
    ob = V._mesh_from_voxels(name, vox, scale=unit, pal=PAL)
    zmin = min(z for _, _, z, _ in vox)
    for v in ob.data.vertices:
        v.co.z -= zmin * unit
    mat = bpy.data.materials.new("M_BB_" + name)
    mat.use_nodes = True
    top = max(set(c for *_, c in vox), key=[c for *_, c in vox].count)  # preview/base tint; vertex colours carry detail
    mat.diffuse_color = tuple(PAL[top]) + (1.0,)
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = tuple(PAL[top]) + (1.0,)
    ob.data.materials.append(mat)
    xs = [v.co for v in ob.data.vertices]
    lo = [min(p[i] for p in xs) for i in range(3)]
    hi = [max(p[i] for p in xs) for i in range(3)]
    mesh = bpy.data.meshes.new("UCX_" + name)
    cx = [(a, b, c) for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])]
    mesh.from_pydata(cx, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    ucx = bpy.data.objects.new("UCX_" + name, mesh)
    bpy.context.scene.collection.objects.link(ucx)
    side = []
    for sn, (p, _) in socks.items():
        loc = (p[0] * unit, p[1] * unit, (p[2] - zmin) * unit)
        e = bpy.data.objects.new(sn, None)
        e.location = loc
        bpy.context.scene.collection.objects.link(e)
        side.append({"name": sn, "parent": "", "location": _ue(loc), "rotation": [0, 0, 0]})
    d = os.path.join(out_root, name)
    os.makedirs(d, exist_ok=True)
    glb = os.path.join(d, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_extras=True)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    size = [round(hi[i] - lo[i], 3) for i in range(3)]
    with open(os.path.join(d, name + ".sockets.json"), "w", encoding="utf-8") as f:
        json.dump({"asset": name, "units": "cm", "space": "unreal", "sockets": side}, f, indent=1)
    meta = {"name": name, "realm": "Prismheart Realm", "kind": kind, "voxel_cm": cm, "voxels": len(vox), "tris": tris,
            "size_m": size, "pivot": "bottom-centre", "front": "Blender -Y (place with yaw -90)", "collision": "UCX_" + name,
            "sockets": [s["name"] for s in side], "status": "NOT READY"}
    with open(os.path.join(d, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    return meta


def main(argv):
    out = argv[0]
    names = argv[1].split(",") if len(argv) > 1 else list(CATALOG)
    metas = [build(n, out) for n in names]
    man = {"schema": "daedalus.blender.arcade_prism/v1", "generated_by": "tools/blender/arcade_prism_props.py",
           "realm": "prismheart_realm", "anchor": "arcade_plaza", "status": "NOT READY",
           "hook": {"cabinet": "SOCKET_Floor -> realm-cabinets.json slot; UI on SOCKET_Screen/SOCKET_Marquee",
                    "sphere": "SOCKET_Facet_0..5 <- facet SOCKET_Seat", "vfx": "SOCKET_Glow / SOCKET_Core"},
           "assets": metas}
    with open(os.path.join(out, "arcade_prism_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    print("BUILT", len(metas), [(m["name"], m["tris"], m["size_m"]) for m in metas])


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if a:
        main(a)
    else:
        print(len(CATALOG), "assets", [n for n in CATALOG if not plan(n)[0]])
