# SPDX-License-Identifier: MIT
"""Team Claude's contest island (2026-10-14 09:29: "team codex vs team claude, who makes the best and most islands").

A voxel island from a seed, in the look of the contest reference (docs/production/reference): grass top with a
dirt band and a grey rock mass that narrows to a jagged underside, a sandy rim, a pond basin with a waterfall sheet
pouring off the edge, tree clusters with round canopies, two or three blossom trees, a cottage with a red roof and
lit windows, flower drifts, a few rocks, crystals hanging below, clouds nearby. One voxel = 1 m. Everything is one
mesh per layer (island / water / trees / cottage / flowers / rocks / crystals / clouds) coloured by vertex colour,
exported as a GLB with the island's origin at the top centre (walk surface at Z=0) and a convex UCX for the body.

Run inside Blender (bpy):   exec(open(r'...\\voxel_island.py').read()); build(seed=240, out=r'C:\\...\\Island_C240.glb')
"""
import math
import os
import random

try:
    import bpy
    import bmesh
except ImportError:   # unit tests run the planner without Blender
    bpy = None

# ---- the plan (pure) ------------------------------------------------------------------------------------------

PAL = {
    "grass": (0.36, 0.62, 0.27), "grass2": (0.42, 0.68, 0.30), "dirt": (0.45, 0.31, 0.19), "dirt2": (0.52, 0.37, 0.22),
    "rock": (0.42, 0.40, 0.46), "rock2": (0.36, 0.34, 0.41), "sand": (0.80, 0.72, 0.52), "water": (0.35, 0.62, 0.90),
    "foam": (0.80, 0.90, 1.00), "trunk": (0.40, 0.26, 0.15), "leaf": (0.25, 0.55, 0.22), "leaf2": (0.33, 0.66, 0.28),
    "blossom": (0.93, 0.60, 0.78), "blossom2": (0.98, 0.75, 0.86), "wall": (0.82, 0.72, 0.55), "roof": (0.70, 0.22, 0.20),
    "window": (1.00, 0.90, 0.55), "door": (0.35, 0.22, 0.12), "flower_r": (0.90, 0.25, 0.30), "flower_y": (0.95, 0.85, 0.25),
    "flower_w": (0.95, 0.95, 0.95), "crystal": (0.75, 0.55, 0.95), "crystal2": (0.55, 0.85, 0.95), "cloud": (0.97, 0.97, 0.99),
}


def plan(seed, size=46, thick=22):
    """{layer: [(x, y, z, colour)]} voxels for one island, 1 m each, centred at (0,0), walk surface at z=0.
    size = island radius in voxels (46 -> 92 m), thick = rock depth below the rim."""
    rng = random.Random(seed)
    vox = {k: [] for k in ("island", "water", "trees", "cottage", "flowers", "rocks", "crystals", "clouds")}
    # 1. footprint: a blobby disc (3 harmonics), the rim 2 m below the top so the top is a plateau
    harm = [(rng.uniform(0.04, 0.10), rng.randint(2, 5), rng.uniform(0, 6.28)) for _ in range(3)]

    def radius(ang):
        return size * (1.0 + sum(a * math.sin(n * ang + p) for a, n, p in harm))

    top = {}   # (x,y) -> True inside
    for x in range(-size - 6, size + 7):
        for y in range(-size - 6, size + 7):
            r = math.hypot(x + 0.5, y + 0.5)
            if r <= radius(math.atan2(y + 0.5, x + 0.5)):
                top[(x, y)] = r
    # pond: a basin 10 m across off-centre, with a waterfall notch toward the rim
    pang = rng.uniform(0, 6.28)
    pr = size * 0.45
    pcx, pcy = int(pr * math.cos(pang)), int(pr * math.sin(pang))
    pond = {(x, y) for (x, y) in top if math.hypot(x - pcx, y - pcy) <= 5.5}
    notch_dir = (math.cos(pang), math.sin(pang))
    notch = {(x, y) for (x, y) in top if 0 <= ((x - pcx) * notch_dir[0] + (y - pcy) * notch_dir[1]) and abs((x - pcx) * -notch_dir[1] + (y - pcy) * notch_dir[0]) <= 1.5}
    # 2. the body: top grass layer, dirt band, rock narrowing to a jagged keel
    for (x, y), r in top.items():
        edge = radius(math.atan2(y + 0.5, x + 0.5)) - r
        rim = edge < 2.0
        in_pond = (x, y) in pond
        in_notch = (x, y) in notch and not in_pond and edge < 6
        ztop = -1 if rim else 0
        if in_pond:
            ztop = -2
        if in_notch:
            ztop = -2
        colour = "sand" if rim else ("grass" if rng.random() < 0.7 else "grass2")
        if in_pond or in_notch:
            colour = "dirt2"
        vox["island"].append((x, y, ztop, colour))
        for z in range(ztop - 1, ztop - 4, -1):
            vox["island"].append((x, y, z, "dirt" if rng.random() < 0.7 else "dirt2"))
        depth = int(thick * (1.0 - (r / max(radius(math.atan2(y + 0.5, x + 0.5)), 1.0)) ** 1.6) + rng.randint(-2, 2))
        for z in range(ztop - 4, ztop - 4 - max(depth, 1), -1):
            vox["island"].append((x, y, z, "rock" if rng.random() < 0.6 else "rock2"))
    # 3. water: pond surface and the waterfall sheet
    for (x, y) in pond:
        vox["water"].append((x, y, -1, "water"))
    for (x, y) in notch:
        if (x, y) in top and (x, y) not in pond:
            vox["water"].append((x, y, -1, "water"))
    fx, fy = max(notch, key=lambda p: math.hypot(p[0], p[1])) if notch else (pcx, pcy)
    for z in range(-1, -thick - 6, -1):
        vox["water"].append((fx, fy, z, "water" if z % 3 else "foam"))
        vox["water"].append((fx + int(round(-notch_dir[1])), fy + int(round(notch_dir[0])), z, "water"))
    # 4. cottage on the high side opposite the pond
    cx, cy = int(-pr * 0.6 * math.cos(pang)), int(-pr * 0.6 * math.sin(pang))
    w, d, h = 7, 6, 4
    for x in range(cx - w // 2, cx + w // 2 + 1):
        for y in range(cy - d // 2, cy + d // 2 + 1):
            for z in range(1, h + 1):
                shell = x in (cx - w // 2, cx + w // 2) or y in (cy - d // 2, cy + d // 2)
                if shell:
                    c = "wall"
                    if z in (2, 3) and ((x - cx) % 3 == 0) and y == cy - d // 2:
                        c = "window"
                    if z in (1, 2) and x == cx and y == cy + d // 2:
                        c = "door"
                    vox["cottage"].append((x, y, z, c))
    for k in range(4):   # gable roof
        for x in range(cx - w // 2 - 1 + k, cx + w // 2 + 2 - k):
            for y in range(cy - d // 2 - 1, cy + d // 2 + 2):
                vox["cottage"].append((x, y, h + 1 + k, "roof"))
    # 5. trees: 3 clusters of 3-5 round-canopy trees + 2-3 blossom trees, away from pond/cottage
    def free(x, y, m=3):
        return (x, y) in top and top[(x, y)] < radius(math.atan2(y, x)) - 4 and math.hypot(x - pcx, y - pcy) > 8 and (abs(x - cx) > w // 2 + m or abs(y - cy) > d // 2 + m)

    def tree(x, y, kind):
        hgt = rng.randint(4, 7)
        for z in range(1, hgt + 1):
            vox["trees"].append((x, y, z, "trunk"))
        rad = rng.randint(2, 3)
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                for dz in range(-rad + 1, rad + 1):
                    if dx * dx + dy * dy + dz * dz <= rad * rad + 1:
                        c = ("blossom" if rng.random() < 0.7 else "blossom2") if kind == "blossom" else ("leaf" if rng.random() < 0.6 else "leaf2")
                        vox["trees"].append((x + dx, y + dy, hgt + dz, c))
    for _ in range(3):
        for _try in range(40):
            ax, ay = rng.randint(-size, size), rng.randint(-size, size)
            if free(ax, ay):
                break
        for _ in range(rng.randint(3, 5)):
            tx, ty = ax + rng.randint(-5, 5), ay + rng.randint(-5, 5)
            if free(tx, ty):
                tree(tx, ty, "leaf")
    for _ in range(rng.randint(2, 3)):
        for _try in range(40):
            tx, ty = rng.randint(-size, size), rng.randint(-size, size)
            if free(tx, ty):
                tree(tx, ty, "blossom")
                break
    # 6. flowers, rocks
    for _ in range(rng.randint(60, 110)):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if free(x, y, 1):
            vox["flowers"].append((x, y, 1, rng.choice(("flower_r", "flower_y", "flower_w"))))
    for _ in range(rng.randint(4, 8)):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if free(x, y, 2):
            for dx in range(0, rng.randint(1, 3)):
                for dy in range(0, rng.randint(1, 2)):
                    for dz in range(1, rng.randint(2, 3)):
                        vox["rocks"].append((x + dx, y + dy, dz, "rock" if rng.random() < 0.5 else "rock2"))
    # 7. crystals hanging below the keel, clouds beside
    for _ in range(rng.randint(3, 6)):
        x, y = rng.randint(-size // 2, size // 2), rng.randint(-size // 2, size // 2)
        ln = rng.randint(4, 9)
        c = rng.choice(("crystal", "crystal2"))
        for z in range(-thick - 4, -thick - 4 - ln, -1):
            vox["crystals"].append((x, y, z, c))
            if ln > 6 and z > -thick - 6:
                vox["crystals"].append((x + 1, y, z, c))
    for _ in range(rng.randint(2, 3)):
        ang = rng.uniform(0, 6.28)
        cx0, cy0, cz0 = int((size + 18) * math.cos(ang)), int((size + 18) * math.sin(ang)), rng.randint(6, 14)
        for dx in range(-6, 7):
            for dy in range(-3, 4):
                for dz in range(0, 3):
                    if dx * dx / 36.0 + dy * dy / 9.0 + (dz - 1) ** 2 / 2.0 <= 1.0 + rng.uniform(-0.2, 0.2):
                        vox["clouds"].append((cx0 + dx, cy0 + dy, cz0 + dz, "cloud"))
    return vox


def stats(vox):
    return {k: len(v) for k, v in vox.items()}


# ---- Blender side ---------------------------------------------------------------------------------------------

def _mesh_from_voxels(name, voxels, scale=100.0):
    """One mesh: a unit cube per voxel (only outer faces), vertex colours from the palette. scale: cm per voxel."""
    occupied = {(x, y, z) for x, y, z, _ in voxels}
    colour = {(x, y, z): c for x, y, z, c in voxels}
    bm = bmesh.new()
    layer = bm.loops.layers.color.new("Col")
    faces = [((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))), ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
             ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))), ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
             ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))), ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)))]
    cache = {}
    for (x, y, z) in occupied:
        col = PAL[colour[(x, y, z)]] + (1.0,)
        for (nx, ny, nz), quad in faces:
            if (x + nx, y + ny, z + nz) in occupied:
                continue
            verts = []
            for (qx, qy, qz) in quad:
                key = (x + qx, y + qy, z + qz)
                v = cache.get(key)
                if v is None:
                    v = bm.verts.new(((x + qx) * scale, (y + qy) * scale, (z + qz) * scale))
                    cache[key] = v
                verts.append(v)
            try:
                f = bm.faces.new(verts)
            except ValueError:
                continue
            for loop in f.loops:
                loop[layer] = col
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.get("VoxelVertexColour")
    if mat is None:
        mat = bpy.data.materials.new("VoxelVertexColour")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        vc = nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        mat.node_tree.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.85
    me.materials.append(mat)
    return ob


GROUPS = {"body": ("island", "water", "trees", "cottage", "flowers", "rocks", "crystals"), "clouds": ("clouds",)}


def build(seed, out, size=46, thick=22, keep=False):
    """Build the island for `seed` in the open Blender scene and export it to `out` (GLB), plus a UCX convex hull
    of the body as a sibling FBX. Returns stats."""
    vox = plan(seed, size, thick)
    name = "Island_C%d" % seed
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Island_C"):
            bpy.data.objects.remove(ob, do_unlink=True)
    objs = []
    for layer, members in GROUPS.items():      # two meshes per island: Unreal's importer costs ~2 s per mesh
        voxels = [v for m in members for v in vox.get(m, [])]
        if voxels:
            objs.append(_mesh_from_voxels("%s_%s" % (name, layer), voxels))
    for ob in bpy.data.objects:
        ob.select_set(ob in objs)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format="GLB", export_apply=True, export_yup=True)
    # collision: a convex hull of the island body only
    body = bpy.data.objects.get("%s_body" % name)
    if body is not None:
        hull = body.copy()
        hull.data = body.data.copy()
        hull.name = "UCX_%s_00" % name
        bpy.context.scene.collection.objects.link(hull)
        bpy.context.view_layer.objects.active = hull
        for ob in bpy.data.objects:
            ob.select_set(ob is hull)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode="OBJECT")
        for ob in bpy.data.objects:
            ob.select_set(ob is hull or ob is body)
        bpy.ops.export_scene.fbx(filepath=out[:-4] + ".fbx", use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
        if not keep:
            bpy.data.objects.remove(hull, do_unlink=True)
    if not keep:
        for ob in objs:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {"seed": seed, "out": out, "voxels": stats(vox)}


def build_many(seeds, out_dir, size=46, thick=22):
    """Contest batches (Richey 09:36 "chunks of 10 then scale up"): one GLB per seed into out_dir. Returns
    {seed: stats}; a seed whose GLB already exists is skipped so a re-run only fills gaps."""
    done = {}
    for seed in seeds:
        out = os.path.join(out_dir, "Island_C%d.glb" % seed)
        if os.path.exists(out):
            done[seed] = "exists"
            continue
        done[seed] = build(seed, out, size=size, thick=thick)
    return done
