# SPDX-License-Identifier: MIT
"""Team Claude's voxel islands as members of Ultra's Super Island standard (buckwild-sol, branch
codex/lumenwake-super-island: docs/production/SUPER-ISLAND-DESIGN.md + LUMENWAKE-ISLAND-STANDARD.md).

Contract we follow: 1 unit = 1 m; plot root at (0, 0, 0) with the walkway deck datum at Z = 10 m; 256 m cell
pitch; 240 m mature envelope; cardinal sockets Connect_E/N/W/S at local (+-120, 0) / (0, +-120); 8 m clear walking
width with a 12 m dressed landing; adjacent sockets 16 m apart, spanned by a separate bridge piece; four or more
distinct connected members make a Super Island. Members keep their own seed, kind and chemistry manifest.

    import voxel_super_island as S
    S.member_plan(seed, kind)   -> voxels of one 240 m-envelope member with four landings and sockets
    S.plan(seed, kinds)         -> four members at (+-128, +-128) + bridges + sky rivers, and the layout manifest
    S.build(seed, out_fbx)      -> FBX (body / water / clouds + UCX) + <out>.super-island.json (Blender)

If `super_island_layout.py` (Ultra's helper) is importable, its `layout_plots` supplies positions, sockets and
connectors; otherwise the same default 2x2 profile is derived here so the geometry is identical either way.
"""
import json
import math
import os

import hero_island as H
import island_chemistry as CH
import island_cluster as X
import voxel_island as V

PITCH, SPAN, DATUM, SOCKET_R, WALK_W, LANDING_W = 256.0, 240.0, 10.0, 120.0, 8.0, 12.0
SOCKETS = (("E", 1, 0), ("N", 0, 1), ("W", -1, 0), ("S", 0, -1))
MEMBER_SIZE = 104          # voxels of radius -> ~208 m across + landings reach 120 m


def _layout(members):
    try:
        import super_island_layout as L
        return L.layout_plots(members, columns=2, pitch=PITCH, span=SPAN, datum=DATUM)
    except Exception:
        cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
        half = PITCH / 2.0
        plots, connectors = [], []
        for m, (e, n) in zip(members, cells):
            x, y = -half + e * PITCH, -half + n * PITCH
            socks = [{"name": "Connect_" + s, "side": s, "position": [dx * SOCKET_R, dy * SOCKET_R, DATUM],
                      "worldPosition": [x + dx * SOCKET_R, y + dy * SOCKET_R, DATUM], "outward": [dx, dy, 0],
                      "clearWidth": WALK_W, "walkwayDatum": DATUM} for s, dx, dy in SOCKETS]
            plots.append({"plot": m, "cell": [e, n], "position": [x, y, 0.0], "sockets": socks})
        lookup = {tuple(p["cell"]): p for p in plots}
        for p in plots:
            e, n = p["cell"]
            for s, dx, dy in (("E", 1, 0), ("N", 0, 1)):
                q = lookup.get((e + dx, n + dy))
                if q:
                    a = [p["position"][0] + dx * SOCKET_R, p["position"][1] + dy * SOCKET_R, DATUM]
                    b = [q["position"][0] - dx * SOCKET_R, q["position"][1] - dy * SOCKET_R, DATUM]
                    connectors.append({"plots": [p["plot"], q["plot"]], "sides": [s, {"E": "W", "N": "S"}[s]], "start": a, "end": b,
                                       "direction": [dx, dy, 0], "length": PITCH - SPAN, "gap": PITCH - SPAN, "walkWidth": WALK_W, "kind": "bridge"})
        return {"schema": "daedalus.super-island.authoring/v1", "stage": "AUTHORING_GEOMETRY_ONLY", "memberIDs": members,
                "plotCount": len(members), "pitchMetres": PITCH, "spanMetres": SPAN, "walkwayDatumMetres": DATUM,
                "walkWidthMetres": WALK_W, "socketGapMetres": PITCH - SPAN, "coordinates": "east-north-up-metres",
                "plots": plots, "connectors": connectors}


def member_plan(seed, kind="meadow", realm="WORLD-ZERO"):
    """One member: the Skyfall planner at 240 m envelope, lifted so the plateau sits on the 10 m deck datum,
    with a graded 12 m landing out to each cardinal socket at 120 m."""
    vox = H.plan(seed, realm, kind, size=MEMBER_SIZE)
    vox = {k: [(x, y, z + int(DATUM), c) for x, y, z, c in v] for k, v in vox.items()}
    top = {(x, y): z for x, y, z, c in vox["island"] if c in ("grass", "grass2", "sand", "path", "soil")}
    for name, dx, dy in SOCKETS:
        # from the rim inward 6 m to the socket at 120 m, a stone deck at the datum, posts every 4 m, rails
        for i in range(MEMBER_SIZE - 8, int(SOCKET_R) + 1):
            for k in range(-int(LANDING_W // 2), int(LANDING_W // 2)):
                x, y = dx * i - dy * k, dy * i + dx * k
                vox["island"].append((x, y, int(DATUM), "stone" if (i + k) % 2 else "stone2"))
                vox["island"].append((x, y, int(DATUM) - 1, "deepstone"))
                if (x, y) in top:
                    vox["island"].append((x, y, top[(x, y)], "path"))
            if i % 4 == 0:
                for k in (-int(LANDING_W // 2), int(LANDING_W // 2) - 1):
                    x, y = dx * i - dy * k, dy * i + dx * k
                    for z in range(int(DATUM) + 1, int(DATUM) + 3):
                        vox["props"].append((x, y, z, "fence"))
                    for z in range(int(DATUM) - 2, int(DATUM) - 1):
                        vox["props"].append((x, y, z, "trunk"))
        # the socket marker: a lantern post on each side of the mouth
        for k in (-int(WALK_W // 2) - 1, int(WALK_W // 2)):
            x, y = dx * int(SOCKET_R) - dy * k, dy * int(SOCKET_R) + dx * k
            for z in range(int(DATUM) + 1, int(DATUM) + 4):
                vox["props"].append((x, y, z, "trunk"))
            vox["props"].append((x, y, int(DATUM) + 4, "lantern"))
    return vox


def _bridge(out, start, end):
    (ax, ay, az), (bx, by, bz) = start, end
    n = max(int(round(math.hypot(bx - ax, by - ay))), 1)
    dx, dy = (bx - ax) / n, (by - ay) / n
    for i in range(0, n + 1):
        px, py = ax + dx * i, ay + dy * i
        for k in range(-int(WALK_W // 2), int(WALK_W // 2)):
            x, y = int(round(px - dy * k)), int(round(py + dx * k))
            out["props"].append((x, y, int(DATUM), "plank" if i % 2 else "bridge"))
            if i in (0, n) or k in (-int(WALK_W // 2), int(WALK_W // 2) - 1):
                out["props"].append((x, y, int(DATUM) - 1, "board"))        # sills and outer stringers
        for k in (-int(WALK_W // 2) - 1, int(WALK_W // 2)):
            x, y = int(round(px - dy * k)), int(round(py + dx * k))
            out["props"].append((x, y, int(DATUM) + 1, "fence"))
            if i % 4 == 0:
                for z in range(int(DATUM) + 1, int(DATUM) + 4):
                    out["props"].append((x, y, z, "rope"))
                out["props"].append((x, y, int(DATUM) - 2, "trunk"))      # transverse bracket post


def plan(seed, kinds=("meadow", "frost", "mesa", "crystal"), realm="WORLD-ZERO", labels=None):
    labels = labels or ["CLAUDE-%s" % c for c in "ABCD"]
    lay = _layout(labels)
    out = {k: [] for k in H.LAYERS}
    lakes, chem = [], {}
    for i, (p, kind) in enumerate(zip(lay["plots"], kinds)):
        member_seed = seed * 10 + i
        vox = member_plan(member_seed, kind, realm)
        kp = H.KINDS[kind].get("pal", {})
        if kp:
            vox = {k: [(x, y, z, (c + "@" + kind) if c in kp else c) for x, y, z, c in v] for k, v in vox.items()}
        ox, oy = int(round(p["position"][0])), int(round(p["position"][1]))
        vox = X._shift(vox, ox, oy, 0)
        lake = X._lake_of(vox)
        if lake:
            lakes.append(lake)
        chem[p["plot"]] = {"seed": member_seed, "kind": kind, "chemistry": CH.profile(member_seed, realm)}
        for k in out:
            out[k].extend(vox.get(k, []))
    for c in lay["connectors"]:
        _bridge(out, c["start"], c["end"])
    lakes.sort(key=lambda q: -q[2])
    import random
    rng = random.Random(seed)
    for a, b in zip(lakes, lakes[1:]):
        X._sky_river(out, a, b, rng)
    lay["members"] = chem
    lay["author"] = "team-claude voxel_super_island"
    lay["units"] = "1 voxel = 1 m; FBX at 100 units per voxel (place at scale 0.01); plot root = cluster origin"
    return out, lay


def build(seed, out, kinds=("meadow", "frost", "mesa", "crystal"), realm="WORLD-ZERO", keep=False):
    import bpy
    vox, lay = plan(seed, kinds, realm)
    with open(out[:-4] + ".super-island.json", "w", encoding="utf-8") as f:
        json.dump(lay, f, indent=1)
    pal = X.palette_for("summer")
    pal.update({})
    name = "SuperIsland_C%d" % seed
    for ob in list(bpy.data.objects):
        if ob.name.startswith(name) or ob.name.startswith("UCX_" + name):
            bpy.data.objects.remove(ob, do_unlink=True)
    objs = []
    for layer, members in H.GROUPS.items():
        voxels = [v for m in members for v in vox.get(m, [])]
        if voxels:
            objs.append(V._mesh_from_voxels("%s_%s" % (name, layer), voxels, pal=pal))
    hulls = V._ucx_boxes(name, vox["island"] + [v for v in vox["props"] if v[3] in ("plank", "bridge")], depth=4)
    for ob in bpy.data.objects:
        ob.select_set(ob in objs or ob in hulls)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    if not keep:
        for ob in objs + hulls:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {"seed": seed, "out": out, "voxels": V.stats(vox), "plots": lay["plotCount"]}
