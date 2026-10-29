# SPDX-License-Identifier: MIT
"""Prismheart Arcade Hall floor-plan assembler (blender-team, 2026-10-29, buffffff 57464).
Lays out the modular hall kit (arcade_hall_kit.py) on the 2 m grid and dresses it with the existing arcade assets listed in
docs/art/arcade-prism-20261026/arcade_prism_manifest.json (cabs, counters, light rigs, floor tiles, plush, signs/boards, posters, carpet).

Hall frame: metres, Z up, interior x in [0, 2W], y in [0, 2D], floor top z = 0 (Foundation_2m tops), ceiling plane z = 4.
Every layout has its doorway on the south edge (y = 0); outside is -Y. Props face -Y in their own frame, so yaw 0 faces south.
Attached props ("on": [host index, socket]) read the host's .sockets.json (UE cm, Y flipped) so plush sits on real prize shelves.

  python arcade_hall_assembler.py plan  --manifest <arcade manifest> --staging <bot-team/staging> --out <dir> [--tsv <java resource>]
      -> <dir>/arcade_hall_layouts.json (+ checks: in-bounds, overlaps, door clearance, walk path door -> every Player1/Customer spot)
  blender -b --factory-startup --python arcade_hall_assembler.py -- render --layouts <dir>/arcade_hall_layouts.json --out <dir>
      -> <dir>/layout_<id>_{plan,outside,cutaway}.png per layout (compose with magick)"""
import json, math, os, sys, glob, argparse
G, H = 2.0, 4.0
SEED = 2610291

# id, title, W x D cells, door cell on south edge, windows [(edge, cell)], props [(asset, x, y, yaw[, z])], attached [(asset, host_idx, socket)],
# posters [(decal, edge, cell)], light rigs [(asset, x, y, yaw)], floor {"carpet": cells|"all", "tiles": [(asset, cx, cy)]}
LAYOUTS = [
    dict(id="corner_arcade", title="Corner Arcade (8 x 6 m)", W=4, D=3, door=1, windows=[("E", 1), ("W", 1)],
         props=[("Prop_Arcade_Cab_Prismheart", 1.2, 5.35, 0), ("Prop_Arcade_Cab_Shardring", 2.1, 5.35, 0), ("Prop_Arcade_Cab_Waystone", 3.0, 5.35, 0),
                ("Prop_Arcade_Cab_ClawCrane", 6.9, 5.2, 0), ("Prop_Arcade_Cab_Cocktail", 5.0, 3.0, 0), ("Prop_Arcade_Stool", 5.0, 2.25, 0),
                ("Prop_Arcade_Stool", 5.0, 3.75, 0), ("Prop_Arcade_TokenMachine", 0.55, 1.0, 90), ("Prop_Arcade_TicketCounter", 7.55, 1.0, -90),
                ("Prop_Arcade_HighScoreBoard", 5.0, 5.84, 0)],
         attached=[], posters=[("Decal_Arcade_Poster_StarRun", "W", 2), ("Decal_Arcade_Poster_CometCup", "E", 2)],
         lights=[("Prop_Arcade_CeilingLightRig_B", 3.0, 3.0, 0), ("Prop_Arcade_CeilingLightRig_A", 5.0, 5.0, 0)],
         floor=dict(carpet="all", tiles=[]), signs=[("Prop_ArcadeHall_Sign_Prismheart", "N", 1, 3.3), ("Prop_ArcadeHall_Sign_PlayArrow", "W", 0, 3.0)]),
    dict(id="prize_hall", title="Prize Hall (12 x 8 m)", W=6, D=4, door=2, windows=[("E", 1), ("E", 2), ("W", 1), ("W", 2)],
         props=[("Prop_Arcade_PrizeCounter", 6.0, 7.0, 0), ("Prop_Arcade_HighScoreBoard", 9.0, 7.84, 0), ("Prop_Arcade_Cab_DancePad", 2.0, 6.75, 0),
                ("Prop_Arcade_Cab_Pinball", 0.85, 4.0, 90), ("Prop_Arcade_Cab_Pinball", 0.85, 2.4, 90), ("Prop_Arcade_Cab_Prismheart", 11.4, 5.4, -90),
                ("Prop_Arcade_Cab_Shardring", 11.4, 4.5, -90), ("Prop_Arcade_Cab_Waystone", 11.4, 3.6, -90), ("Prop_Arcade_PhotoBooth", 10.9, 1.0, -90),
                ("Prop_Arcade_TicketCounter", 3.6, 0.55, 180), ("Prop_Arcade_TokenMachine", 8.4, 0.55, 180), ("Prop_Arcade_Cab_ClawCrane", 9.4, 6.9, 0)],
         attached=[("Prop_Arcade_Plush_Shardling", 0, "Prize_0"), ("Prop_Arcade_Plush_Waystoad", 0, "Prize_2"), ("Prop_Arcade_Plush_Glimmermoth", 0, "Prize_4"),
                   ("Prop_Arcade_Plush_Pebblepup", 0, "Prize_6"), ("Prop_Arcade_Plush_Lumenfish", 0, "Prize_8")],
         posters=[("Decal_Arcade_Poster_PrismKnight", "N", 3), ("Decal_Arcade_Poster_ShardRacer", "S", 0), ("Decal_Arcade_Poster_StarRun", "S", 4)],
         lights=[("Prop_Arcade_CeilingLightRig_A", 6.0, 4.0, 0), ("Prop_Arcade_CeilingLightRig_C", 2.0, 4.0, 0), ("Prop_Arcade_CeilingLightRig_C", 10.0, 4.0, 0)],
         floor=dict(carpet="all", tiles=[("Prop_Arcade_FloorTile_Checker", 2, 1), ("Prop_Arcade_FloorTile_Checker", 3, 1), ("Prop_Arcade_FloorTile_Checker", 2, 0), ("Prop_Arcade_FloorTile_Checker", 3, 0)]),
         signs=[("Prop_ArcadeHall_Sign_Prizes", "N", 3, 3.45), ("Prop_ArcadeHall_Sign_Prismheart", "S", 4, 3.2), ("Prop_ArcadeHall_Sign_PlayArrow", "W", 3, 3.0)]),
    dict(id="heart_hall", title="Heart Hall (10 x 10 m)", W=5, D=5, door=2, windows=[("E", 2), ("W", 2), ("N", 0), ("N", 4)],
         props=[("Prop_Prism_HeartSphere_Pedestal", 5.0, 5.5, 0), ("Prop_Arcade_Cab_Prismheart", 0.6, 7.5, 90), ("Prop_Arcade_Cab_Shardring", 0.6, 6.6, 90),
                ("Prop_Arcade_Cab_Waystone", 9.4, 7.5, -90), ("Prop_Arcade_Cab_Cocktail", 9.0, 3.0, 0), ("Prop_Arcade_Cab_Pinball", 0.85, 3.0, 90),
                ("Prop_Arcade_Cab_ClawCrane", 3.0, 9.3, 0), ("Prop_Arcade_PhotoBooth", 7.2, 9.25, 0), ("Prop_Arcade_TokenMachine", 1.6, 0.55, 180),
                ("Prop_Arcade_TicketCounter", 8.4, 0.55, 180)],
         attached=[("Prop_Prism_HeartSphere", 0, "Sphere")] + [("Prop_Prism_ShardFacet_" + e, 0, "Rune_%d" % i) for i, e in enumerate(("Fire", "Tide", "Gale", "Stone", "Light", "Shade"))],
         posters=[("Decal_Arcade_Poster_CometCup", "N", 2), ("Decal_Arcade_Poster_PrismKnight", "W", 3), ("Decal_Arcade_Poster_ShardRacer", "E", 3)],
         lights=[("Prop_Arcade_CeilingLightRig_C", 5.0, 5.5, 0), ("Prop_Arcade_CeilingLightRig_B", 3.0, 2.5, 0), ("Prop_Arcade_CeilingLightRig_B", 7.0, 2.5, 0)],
         floor=dict(carpet="all", tiles=[("Prop_Arcade_FloorTile_PrismRay", 2, 2), ("Prop_Arcade_FloorTile_Starfield", 2, 1), ("Prop_Arcade_FloorTile_Starfield", 2, 0)]),
         signs=[("Prop_ArcadeHall_Sign_Prismheart", "N", 2, 3.3), ("Prop_ArcadeHall_Sign_PlayArrow", "E", 1, 3.0), ("Prop_ArcadeHall_Sign_Prizes", "W", 1, 3.0)]),
]
NO_FOOTPRINT = ("Prop_Arcade_HighScoreBoard", "Prop_Arcade_Stool")   # wall-hung board / seats a player uses: in-bounds check only


def rot(x, y, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); return x * c - y * s, x * s + y * c


def find(staging, name, ext):
    hits = sorted(glob.glob(os.path.join(staging, "arcade-*", "**", name + ext), recursive=True)); return hits[-1].replace("\\", "/") if hits else None


def sockets(staging, name):
    p = find(staging, name, ".sockets.json"); d = {}
    for s in json.load(open(p, encoding="utf-8"))["sockets"] if p else []:
        x, y, z = s["location"]; d[s["name"].replace("SOCKET_", "")] = (x / 100.0, -y / 100.0, z / 100.0)
    return d


def wall_pieces(L):
    W, D = L["W"], L["D"]; P = []; win = set(L["windows"])
    for e, n, yaw in (("S", W, 180), ("N", W, 0), ("W", D, 90), ("E", D, -90)):
        for i in range(n):
            if e in "SN": x, y = G * i + 1, (0 if e == "S" else G * D)
            else: x, y = (0 if e == "W" else G * W), G * i + 1
            kind = "Doorway_2m" if (e == "S" and i == L["door"]) else ("Window_2m" if (e, i) in win else "Wall_2m")
            P.append(dict(asset="Prop_ArcadeHall_" + kind, x=x, y=y, z=0, yaw=yaw, edge=e, cell=i))
    for x, y in ((0, 0), (G * W, 0), (0, G * D), (G * W, G * D)): P.append(dict(asset="Prop_ArcadeHall_Corner", x=x, y=y, z=0, yaw=0))
    for i in range(W):
        for j in range(D):
            P.append(dict(asset="Prop_ArcadeHall_Foundation_2m", x=G * i + 1, y=G * j + 1, z=0, yaw=0))
            P.append(dict(asset="Prop_ArcadeHall_CeilingBay_2m", x=G * i + 1, y=G * j + 1, z=H, yaw=0))
    return P


def plan(L, sizes, staging):
    W, D = L["W"], L["D"]; out = dict(id=L["id"], title=L["title"], cells=[W, D], grid_m=G, height_m=H, kit=wall_pieces(L), props=[], decals=[], issues=[])
    for k, (a, x, y, yaw, *z) in enumerate(L["props"]):
        out["props"].append(dict(asset=a, x=x, y=y, z=(z[0] if z else 0.0), yaw=yaw))
    for a, h, s in L["attached"]:
        host = out["props"][h]; S = sockets(staging, host["asset"])
        if s not in S: out["issues"].append("missing socket %s on %s" % (s, host["asset"])); continue
        dx, dy = rot(S[s][0], S[s][1], host["yaw"])
        out["props"].append(dict(asset=a, x=round(host["x"] + dx, 4), y=round(host["y"] + dy, 4), z=round(host["z"] + S[s][2], 4), yaw=host["yaw"], on=[h, s]))
    for a, x, y, yaw in L["lights"]: out["props"].append(dict(asset=a, x=x, y=y, z=H - 0.0, yaw=yaw, hung=True))
    if L["floor"]["carpet"] == "all":
        tiled = {(cx, cy) for _, cx, cy in L["floor"]["tiles"]}
        for i in range(W):
            for j in range(D):
                if (i, j) not in tiled: out["decals"].append(dict(decal="Decal_Arcade_Carpet_Cosmic", x=G * i + 1, y=G * j + 1, z=0.003, yaw=0, size=[2.0, 2.0], plane="floor"))
    for a, cx, cy in L["floor"]["tiles"]: out["props"].append(dict(asset=a, x=G * cx + 1, y=G * cy + 1, z=0.0, yaw=0, floor=True))
    for d, e, i in L["posters"]:
        if e in "SN": x, y, yaw = G * i + 1 + (0.0 if e == "N" else 0.0), (0.105 if e == "S" else G * D - 0.105), (180 if e == "S" else 0)
        else: x, y, yaw = (0.105 if e == "W" else G * W - 0.105), G * i + 1, (90 if e == "W" else -90)
        if e == "S" and i == L["door"]: out["issues"].append("poster %s on the doorway bay" % d)
        out["decals"].append(dict(decal=d, x=x, y=y, z=1.7, yaw=yaw, size=[0.6, 0.9], plane="wall"))
    # signs: wall neons from the layout + the EXIT sign over the doorway, inside face (origin on the wall surface, face into the room)
    out["signs"] = []; inner = 0.1; door = L["door"]
    for a, e, i, z in list(L.get("signs", [])) + [("Prop_ArcadeHall_Sign_DoorInside", "S", door, 3.0)]:
        if e in "SN": x, y, yaw = G * i + 1, (inner if e == "S" else G * D - inner), (180 if e == "S" else 0)
        else: x, y, yaw = (inner if e == "W" else G * W - inner), G * i + 1, (90 if e == "W" else -90)
        out["signs"].append(dict(asset=a, x=x, y=y, z=z, yaw=yaw, edge=e, cell=i, wall=True))
        if (e, i) in set(L["windows"]): out["issues"].append("sign %s on a window bay %s%d" % (a, e, i))
        if e == "S" and i == door and a != "Prop_ArcadeHall_Sign_DoorInside": out["issues"].append("wall sign %s on the doorway bay" % a)
        if z + 0.35 > H - 0.15: out["issues"].append("sign %s hits the crown/ceiling (z %.2f)" % (a, z))
        if a == "Prop_ArcadeHall_Sign_DoorInside" and z - 0.17 < 2.64: out["issues"].append("EXIT sign drops into the door opening")
        for d in out["decals"]:
            if d["plane"] == "wall" and abs(d["x"] - x) < 0.01 + 1.2 * (e in "SN") and abs(d["y"] - y) < 0.01 + 1.2 * (e in "WE") and abs(d["z"] - z) < 0.8:
                out["issues"].append("sign %s overlaps poster %s" % (a, d["decal"]))
    # exterior: steps from island grade (z = -FOUND) to the floor at the doorway, awning over it, then a path of slabs out to the island
    dx = G * door + 1; FOUND = 0.4; out["exterior"] = [dict(asset="Prop_ArcadeHall_EntranceSteps", x=dx, y=-0.1, z=0.0, yaw=0),
                                                         dict(asset="Prop_ArcadeHall_Awning", x=dx, y=-0.1, z=2.72, yaw=0)]
    for k in range(int(L.get("path_tiles", 3))):
        out["exterior"].append(dict(asset="Prop_ArcadeHall_PathTile", x=dx, y=-1.0 - 0.8 - 1.6 * k, z=-FOUND, yaw=0))
    out["island"] = dict(grade_z=-FOUND, steps_bottom=[dx, -1.0, -FOUND], path_end=[dx, -1.0 - 1.6 * int(L.get("path_tiles", 3)), -FOUND])
    check(out, sizes, staging); return out


def foot(p, sizes):
    sx, sy = sizes[p["asset"]][:2]; pts = [rot(u * sx / 2, v * sy / 2, p["yaw"]) for u in (-1, 1) for v in (-1, 1)]
    return (p["x"] + min(q[0] for q in pts), p["y"] + min(q[1] for q in pts), p["x"] + max(q[0] for q in pts), p["y"] + max(q[1] for q in pts))


def check(out, sizes, staging):
    sizes = dict(sizes)
    W, D = out["cells"]; X, Y = G * W, G * D; m = 0.1
    floor = [p for p in out["props"] if not p.get("hung") and not p.get("floor") and "on" not in p]
    boxes = []
    for k, p in enumerate(floor):
        if p["asset"] not in sizes: out["issues"].append("unknown asset " + p["asset"]); continue
        b = foot(p, sizes)
        if b[0] < m - 1e-6 or b[1] < m - 1e-6 or b[2] > X - m + 1e-6 or b[3] > Y - m + 1e-6: out["issues"].append("%s #%d pokes through a wall %s" % (p["asset"], k, [round(v, 2) for v in b]))
        if p["asset"] not in NO_FOOTPRINT: boxes.append((p["asset"], b))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            if a[0] < b[2] - 0.01 and b[0] < a[2] - 0.01 and a[1] < b[3] - 0.01 and b[1] < a[3] - 0.01: out["issues"].append("overlap %s / %s" % (boxes[i][0], boxes[j][0]))
    door = [p for p in out["kit"] if p["asset"].endswith("Doorway_2m")][0]; dz = (door["x"] - 0.8, 0.0, door["x"] + 0.8, 1.6)
    for a, b in boxes:
        if b[0] < dz[2] and dz[0] < b[2] and b[1] < dz[3] and dz[1] < b[3]: out["issues"].append("%s blocks the doorway clear zone" % a)
    # walk grid 0.25 m, player radius 0.3 m
    s = 0.25; nx, ny = int(X / s), int(Y / s); r = 0.3
    free = [[all(not (b[0] - r < (i + .5) * s < b[2] + r and b[1] - r < (j + .5) * s < b[3] + r) for _, b in boxes) and r < (i + .5) * s < X - r and r < (j + .5) * s < Y - r
             for j in range(ny)] for i in range(nx)]
    start = (int(door["x"] / s), int(0.5 / s)); seen = {start}; q = [start]
    if not free[start[0]][start[1]]: out["issues"].append("doorway entry cell is blocked")
    else:
        while q:
            i, j = q.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < nx and 0 <= b < ny and free[a][b] and (a, b) not in seen: seen.add((a, b)); q.append((a, b))
    reach = []
    for k, p in enumerate(floor):
        S = sockets(staging, p["asset"])
        for nm in [n for n in S if n.startswith("Player") or n in ("Customer", "Entry")]:
            lx, ly = S[nm][0], S[nm][1]; sx, sy = sizes.get(p["asset"], (0, 0, 0))[:2]
            if abs(lx) < sx / 2 and abs(ly) < sy / 2: ly = -sy / 2 - 0.3     # spot on the prop itself (dance stage): step-on edge at the front
            dx, dy = rot(lx, ly, p["yaw"]); x, y = p["x"] + dx, p["y"] + dy; ci, cj = int(x / s), int(y / s)
            ok = any((ci + a, cj + b) in seen for a in range(-2, 3) for b in range(-2, 3))   # within ~0.6 m
            reach.append(dict(prop=k, asset=p["asset"], socket=nm, ok=ok))
            if not ok: out["issues"].append("cannot walk from the door to %s.%s" % (p["asset"], nm))
    out["walk"] = dict(cell_m=s, player_radius_m=r, reachable_cells=len(seen), spots=reach)
    out["entry"] = dict(door_socket_world=[door["x"], 0.0, 0.0], spawn_inside=[door["x"], 1.2, 0.0], spawn_outside=[door["x"], -1.2, 0.0], facing_inside=[0, 1, 0])


def main_plan(o):
    m = json.load(open(o.manifest, encoding="utf-8")); sizes = {}

    def walk(v):
        if isinstance(v, dict):
            if isinstance(v.get("name"), str) and v.get("size_m"): sizes[v["name"]] = v["size_m"]
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    walk(m)
    res = dict(schema="arcade-hall-layouts/v1", generated_by="tools/blender/arcade_hall_assembler.py", seed=SEED, status="NOT READY", units="m, Z up, hall frame (door on south edge, outside -Y)",
               kit=sorted({p for L in LAYOUTS for p in [k["asset"] for k in wall_pieces(L)]} | {"Prop_ArcadeHall_Sign_DoorInside"} | {x[0] for L in LAYOUTS for x in L.get("signs", [])} | {"Prop_ArcadeHall_EntranceSteps", "Prop_ArcadeHall_Awning", "Prop_ArcadeHall_PathTile"}), source_manifest=o.manifest.replace("\\", "/"), layouts=[plan(L, sizes, o.staging) for L in LAYOUTS])
    for L in res["layouts"]: L["counts"] = dict(kit=len(L["kit"]), props=len(L["props"]), decals=len(L["decals"]), signs=len(L["signs"]), exterior=len(L["exterior"]))
    os.makedirs(o.out, exist_ok=True); p = os.path.join(o.out, "arcade_hall_layouts.json")
    open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(res, indent=1) + "\n")
    for L in res["layouts"]: print(L["id"], L["counts"], "reach", sum(s["ok"] for s in L["walk"]["spots"]), "/", len(L["walk"]["spots"]), "issues:", L["issues"] or "none")
    if o.tsv:
        lines = ["# arcade-hall-layouts/v1 (generated by tools/blender/arcade_hall_assembler.py; do not hand-edit)", "# id\ttitle\tcellsW\tcellsD\tdoorCell\tspawnInsideX\tspawnInsideY\tprops\tcabs"]
        for L in res["layouts"]:
            cabs = sum(1 for q in L["props"] if "_Cab_" in q["asset"])
            lines.append("\t".join(map(str, (L["id"], L["title"], L["cells"][0], L["cells"][1], [k["cell"] for k in L["kit"] if k["asset"].endswith("Doorway_2m")][0],
                                             L["entry"]["spawn_inside"][0], L["entry"]["spawn_inside"][1], len(L["props"]), cabs))))
        open(o.tsv, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


# ---------------- Blender render ----------------
def main_render(o):
    import bpy, mathutils
    res = json.load(open(o.layouts, encoding="utf-8")); staging = o.staging
    for L in res["layouts"]:
        bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; cache = {}
        groups = {"ceiling": [], "south": [], "east": [], "all": []}

        def place(name, x, y, z, yaw, tag=None):
            if name not in cache:
                p = find(staging, name, ".glb")
                if not p: print("MISSING", name); return
                before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=p); bpy.context.view_layer.update()
                new = list(set(bpy.data.objects) - before)
                cache[name] = [(ob, ob.matrix_world.copy()) for ob in new if ob.type == "MESH" and not ob.name.startswith(("UCX_", "Icosphere"))]
                for ob in new: ob.hide_render = True
                for ob, _ in cache[name]:     # glow panels / big emissive ceiling surfaces were blowing out the inside views
                    for ms in ob.material_slots:
                        mt = ms.material
                        if mt and mt.use_nodes and "Principled BSDF" in mt.node_tree.nodes and ("glow panel" in mt.name.lower() or "CeilingBay" in name):
                            bs = mt.node_tree.nodes["Principled BSDF"]; bs.inputs["Emission Strength"].default_value = min(bs.inputs["Emission Strength"].default_value, 0.25)
            for ob, mw in cache[name]:
                c = ob.copy(); c.parent = None; c.hide_render = False; sc.collection.objects.link(c)
                c.matrix_world = mathutils.Matrix.Translation((x, y, z)) @ mathutils.Matrix.Rotation(math.radians(yaw), 4, "Z") @ mw
                groups["all"].append(c)
                if tag: groups[tag].append(c)
        for k in L["kit"]:
            tag = "ceiling" if "Ceiling" in k["asset"] else ("south" if k.get("edge") == "S" or (k["asset"].endswith("Corner") and k["y"] == 0) else ("east" if k.get("edge") == "E" or (k["asset"].endswith("Corner") and k["x"] > 0) else None))
            place(k["asset"], k["x"], k["y"], k["z"], k["yaw"], tag)
        for p in L["props"]: place(p["asset"], p["x"], p["y"], p["z"], p["yaw"], "ceiling" if p.get("hung") else None)
        for p in L.get("exterior", []): place(p["asset"], p["x"], p["y"], p["z"], p["yaw"])
        bpy.ops.mesh.primitive_plane_add(size=1); gp = bpy.context.active_object; gp.scale = (L["cells"][0] * G + 12, L["cells"][1] * G + 16, 1)
        gp.location = (L["cells"][0] * G / 2, L["cells"][1] * G / 2 - 4, L.get("island", {}).get("grade_z", -0.4) - 0.002); gm = bpy.data.materials.new("island grass"); gm.use_nodes = True
        gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.3, 0.12, 1); gp.data.materials.append(gm)
        for p in L.get("signs", []): place(p["asset"], p["x"], p["y"], p["z"], p["yaw"], "south" if p["edge"] == "S" else ("east" if p["edge"] == "E" else None))
        for d in L["decals"]:
            bc = glob.glob(os.path.join(staging, "arcade-*", "decals", d["decal"], "T_*_BC.png"))
            bpy.ops.mesh.primitive_plane_add(size=1); pl = bpy.context.active_object; pl.scale = (d["size"][0], d["size"][1], 1)
            if d["plane"] == "wall": pl.rotation_euler = (math.radians(90), 0, math.radians(d["yaw"]))
            else: pl.rotation_euler = (0, 0, math.radians(d["yaw"]))
            pl.location = (d["x"], d["y"], d["z"]); mt = bpy.data.materials.new(d["decal"]); mt.use_nodes = True
            if bc:
                tx = mt.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(bc[0]); bs = mt.node_tree.nodes["Principled BSDF"]
                mt.node_tree.links.new(tx.outputs[0], bs.inputs["Base Color"])
                if d["plane"] == "wall": mt.node_tree.links.new(tx.outputs[0], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 0.4
            pl.data.materials.append(mt); groups["all"].append(pl)
        W, D = L["cells"][0] * G, L["cells"][1] * G
        for p in L["props"]:
            if p.get("hung"):
                ld = bpy.data.lights.new("rig", "AREA"); ld.size = 2.0; ld.energy = 220; ld.color = (1.0, 0.85, 1.0); lo = bpy.data.objects.new("rig", ld); lo.location = (p["x"], p["y"], 3.0); sc.collection.objects.link(lo)
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 2.5; sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(sun)
        w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.7, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6; sc.world = w
        sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = True; sc.render.resolution_x, sc.render.resolution_y = 1200, 900
        sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = "ORTHO"
        ctr = mathutils.Vector((W / 2, D / 2, 1.0))
        views = [("plan", ("ceiling",), (W / 2, D / 2, 30), max(W, D * 4 / 3) * 1.08), ("outside", (), (W / 2 + 14, -16, 13), max(W, D) * 1.7), ("cutaway", ("ceiling", "south", "east"), (W / 2 + 14, -16, 15), max(W, D) * 1.55), ("inside", (), None, None)]
        for vn, hide, pos, scale in views:
            for g in ("ceiling", "south", "east"):
                for ob in groups[g]: ob.hide_render = g in hide
            if vn == "inside":     # player's view back toward the doorway: EXIT sign, doorway, south-wall signs
                dx = [k["x"] for k in L["kit"] if k["asset"].endswith("Doorway_2m")][0]
                cam.data.type = "PERSP"; cam.data.lens = 18; cam.location = (dx, min(D - 0.6, 4.0), 1.9)
                cam.rotation_euler = (mathutils.Vector((dx, 0.0, 2.2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
            else:
                cam.data.type = "ORTHO"; cam.location = pos; cam.data.ortho_scale = scale
                cam.rotation_euler = (ctr - mathutils.Vector(pos)).to_track_quat("-Z", "Y").to_euler() if vn != "plan" else (0, 0, 0)
            sc.render.filepath = os.path.join(o.out, "layout_%s_%s.png" % (L["id"], vn)); bpy.ops.render.render(write_still=True); print("RENDERED", sc.render.filepath)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=("plan", "render")); ap.add_argument("--manifest"); ap.add_argument("--staging", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--layouts"); ap.add_argument("--tsv"); o = ap.parse_args(argv)
    main_plan(o) if o.mode == "plan" else main_render(o)
