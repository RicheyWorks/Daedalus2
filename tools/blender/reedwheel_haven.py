# SPDX-License-Identifier: MIT
"""Reedwheel Haven (r1): a spring-water refuge land with a crafted walkway, a repair station and an ecology keeper.

Team Claude's Blender package for PootScoot's assignment 32381.
  * Land id: reedwheel-haven-841025-r1. This is an AUTHORING id, not a deed or NFT.
  * BEFORE reference: Octet_Spring_1. It is read only, never written, and its hashes are pinned in the manifest.

The island is hd_island.build() on the meadow kind. Seed 841025 is the first seed from 841024 up (PootScoot's candidate) whose rolled chemistry (island_chemistry.profile)
agrees with the story; no chemistry is invented. Rolled values:
  * power: water_wheel, drive "the stream"
  * power_unit.salvageable: true, so the wheel starts broken
  * water.filter_needed: true, spring_purity 0.40
  * fish: glassfin and rillperch (rillperch runs in spring)

On top of the island, kit_waterworks adds:
  * a breastshot waterwheel. Its ROTOR is a separate mesh pivoted on the axle, so Unreal can spin it.
  * the flume and frame
  * a boardwalk and footbridge
  * the repair station
  * the reed bed, which is the stream's living filter and the harvest
  * the refuge hut
  * the keeper's post
  * a three-arm signpost

Story: the spring's water runs foul (purity 0.40) since the storm broke the reed-paddled wheel that lifted clean water
to the terraces. The Reed Keeper tends the reed bed, which is what still filters the stream. The player's choice, made
readable by colour:
  * REPAIR (amber): fix the wheel with power-unit parts.
  * HARVEST (reed gold): cut reeds. They are the cheapest paddle and thatch material, but each cut thins the filter.
  * REFUGE (hearth red): shelter at the haven when a wave comes.
The keeper's quest is the balance: repair with bought parts and leave the reeds standing, and the water clears.

Each gameplay row carries a status. Nothing here is bound in Unreal yet:
  * "data": rolled or stored data with no runtime yet.
  * "design": a socket with no host or native authority yet. Where related source exists, the row names it and the
    adapter a host would still need. A source capability is not proof of a binding (PootScoot 32427).

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/reedwheel_haven.py -- OUT_DIR [--render]
Also runs under the bpy module: python reedwheel_haven.py OUT_DIR [--render]. Metres, Z up. The island pivot is the
plateau centre with the deck at z=0. Each role mesh's pivot is its anchor; anchors and yaws are in the layout json.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hd_island as H  # noqa: E402
import kit_waterworks as K  # noqa: E402

REV = "r4"                # r1: first source (dde77fe83); r2: bridge off the farm, spill + foam, dressing (f42e478dc);
                          # r3: honest repair/refuge rows, UCX named for their meshes, post-to-post rails, walk clear of the wheel (591bfc761)
                          # r4: clearance is MEASURED on final geometry (mesh-to-mesh), not a centre distance; adapters on every design row
LAND_ID = "reedwheel-haven-841025-" + REV
CLEARANCE_M = 3.0        # walk-to-wheel minimum vertex distance on final geometry (see build())
SEED = 841025
KIND = "meadow"
REALM = "WORLD-ZERO"
NAME = "ReedwheelHaven_" + REV
BEFORE = {   # read-only reference, pinned 2026-10-15 from D2-build/engines/unreal/art/claude-octets (sha256 prefixes)
    "dir": "D2-build/engines/unreal/art/claude-octets",
    "files": {"Octet_Spring_1_Canal.glb": [407576, "9e2f9e0f92570205"], "Octet_Spring_1.layout.json": [4333, "1a806bd34d38b49b"],
              "Octet_Spring_1.hero.png": [2860675, "6213cd274e96e136"], "Octet_Spring_1.top.png": [3235751, "bac13bb53339c4cf"]},
    "note": "hd_cluster seed 1, plot seeds 100-107; never opened for write by this recipe",
}
STORY = {
    "title": "Reedwheel Haven",
    "premise": "The spring runs foul (purity %s) since a storm broke the reed-paddled wheel that lifted clean water to the terraces. "
               "The Reed Keeper tends the reed bed that still filters the stream.",
    "player_goal": "Choose how to restore the haven: REPAIR the wheel, HARVEST reeds, or take REFUGE when a wave comes. The keeper's "
                   "balance quest rewards repairing with bought parts while the reeds stay standing: the water clears.",
    "choices": {"repair": "amber brass lamp at the station", "harvest": "reed-gold bundles on the drying rack", "refuge": "hearth-red windows of the hut"},
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def role(name, objs, anchor, yaw=0.0):
    """Join a role's parts into one multi-material mesh whose pivot is `anchor` (deck-relative z)."""
    ob = H.join_parts(name, objs)
    ax, ay, az = anchor
    ob.data.transform(__import__("mathutils").Matrix.Translation((-ax, -ay, -az)))
    ob.location = (ax, ay, az)
    H.GROUP.append(ob)
    return ob


def shift(objs, dz):
    for o in objs:
        o.location.z += dz


def build(out_dir):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    H.EXTERNAL_WHEEL = True
    man = H.build(SEED, KIND, out_dir, prefix=NAME + "_Island", realm=REALM, export=False)
    A, h, chem, GP = H.LAST["A"], H.LAST["h"], H.LAST["chem"], H.LAST["GP"]
    island = list(H.GROUP)
    S = A["stream"]
    W = H.WATER

    def unit(a, b):
        d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        return (b[0] - a[0]) / d, (b[1] - a[1]) / d
    sx, sy = unit(S[2], S[4])
    px, py = -sy, sx
    if math.hypot(S[3][0] + px * 9, S[3][1] + py * 9) > math.hypot(S[3][0] - px * 9, S[3][1] - py * 9):
        px, py = -px, -py                                     # +perp points toward the island centre
    yaw = math.atan2(sy, sx)
    wx, wy = S[3]
    at = lambda base, k: (base[0] + px * k, base[1] + py * k)
    taken = [(t[0], t[1], t[2] + 8) for t in A["terraces"]] + [(A["lake"][0], A["lake"][1], max(A["lake"][2], A["lake"][3]) + 4)]

    def site(cands, clear=6.0, max_slope=1.6):
        """First candidate on the island, off every terrace (farm, town, landmark, dock), off the lake, on gentle ground,
        and `clear` metres from anything already sited here. Records the pick so the next site keeps its distance."""
        for c in cands:
            x, y = c
            if not H.inside(x, y, H.R * .9) or any(math.hypot(x - tx, y - ty) < r for tx, ty, r in taken):
                continue
            if max(abs(h(x + 2, y) - h(x - 2, y)), abs(h(x, y + 2) - h(x, y - 2))) > max_slope * 2:
                continue
            taken.append((x, y, clear))
            return c
        raise RuntimeError("no free site among %d candidates" % len(cands))
    ring = lambda base, ks: [at(b, k) for k in ks for b in base]

    n0 = len(H.GROUP)
    wheel = K.waterwheel(H, NAME + "_Wheel", wx, wy, yaw, radius=3.4, width=1.4, paddles=12, broken=4)
    rotor = [o for o in wheel if any(t in o.name for t in ("_Rim", "_Spoke", "_Paddle_", "_Hub"))]
    frame = [o for o in wheel if o not in rotor]
    taken.append((wx, wy, 7))
    st_x, st_y = site(ring([S[3], S[4], S[2]], (10, 12, 14, -10, -12, -14)))
    station = K.repair_station(H, NAME + "_Station", st_x, st_y, h(st_x, st_y), yaw + math.pi / 2, sorted(chem["power_unit"]["parts"]))
    # the crossing: the first stream point whose both bridge ends land clear of every terrace and the lake
    clear_of = lambda q: all(math.hypot(q[0] - tx, q[1] - ty) >= r for tx, ty, r in taken[:len(A["terraces"]) + 1])
    BX = next((S[i] for i in (2, 1, 4) if clear_of(at(S[i], 8)) and clear_of(at(S[i], -8)) and math.hypot(S[i][0] - wx, S[i][1] - wy) > 12), S[2])
    b0, b1 = at(BX, 8), at(BX, -8)
    bridge = K.footbridge(H, NAME + "_Footbridge", b0, b1, W + 1.0)
    near = min(A["path"], key=lambda p: math.hypot(p[0] - st_x, p[1] - st_y))
    # r4 (PootScoot 32503): the walk must clear the wheel by CLEARANCE_M, measured as the minimum 3-D distance between
    # any vertex of the walk (boardwalk + footbridge) and any vertex of the wheel (rotor + frame), on the final
    # geometry. r3 claimed 8 m but only tested centre distances on the original legs; a vertex pair was 4.75 m apart.
    route0 = [near, at(BX, 14), at(BX, 9), b0]

    def detour(push):
        """Route legs that pass the wheel within 8 m + push go behind the repair pad, pushed further out each try.
        Every inserted leg is re-tested (r3 tested only the original legs)."""
        pts = [route0[0]]
        for a, b in zip(route0, route0[1:]):
            for _ in range(4):
                dx, dy = b[0] - pts[-1][0], b[1] - pts[-1][1]
                t = max(0.0, min(1.0, ((wx - pts[-1][0]) * dx + (wy - pts[-1][1]) * dy) / max(1e-6, dx * dx + dy * dy)))
                cx, cy = pts[-1][0] + dx * t, pts[-1][1] + dy * t
                if math.hypot(cx - wx, cy - wy) >= 8 + push or not 0 < t < 1:
                    break
                k = 6.5 + push
                pts.append((st_x + px * k + sx * (k * .4), st_y + py * k + sy * (k * .4)))
                if len(pts) >= 2:                              # the leg INTO the detour must clear too
                    p0, p1 = pts[-2], pts[-1]
                    ex, ey = p1[0] - p0[0], p1[1] - p0[1]
                    tt = max(0.0, min(1.0, ((wx - p0[0]) * ex + (wy - p0[1]) * ey) / max(1e-6, ex * ex + ey * ey)))
                    if math.hypot(p0[0] + ex * tt - wx, p0[1] + ey * tt - wy) < 8 + push:
                        pts.insert(-1, (p0[0] + px * (8 + push), p0[1] + py * (8 + push)))
            pts.append(b)
        return pts
    bpy.context.view_layer.update()                           # matrix_world is stale for new objects until this runs
    wheel_v = [o.matrix_world @ v.co for o in wheel for v in o.data.vertices]
    kd = __import__("mathutils").kdtree.KDTree(len(wheel_v))
    for i, v in enumerate(wheel_v):
        kd.insert(v, i)
    kd.balance()

    def clearance(objs):
        bpy.context.view_layer.update()
        return min(kd.find(o.matrix_world @ v.co)[2] for o in objs for v in o.data.vertices)
    walk = None
    for push in (0, 2, 4, 6, 8, 10):
        if walk:
            for o in walk:
                H.GROUP.remove(o)
                bpy.data.objects.remove(o, do_unlink=True)
        route = detour(push)
        walk = K.boardwalk(H, NAME + "_Boardwalk", route, h)
        walk_clear = clearance(walk + bridge)
        if walk_clear >= CLEARANCE_M:
            break
    if walk_clear < CLEARANCE_M:
        worst = min(((kd.find(o.matrix_world @ v.co)[2], o.name, kd.find(o.matrix_world @ v.co)[1]) for o in walk + bridge for v in o.data.vertices))
        owner = 0
        for o in wheel:
            if worst[2] < owner + len(o.data.vertices):
                break
            owner += len(o.data.vertices)
        raise RuntimeError("walk clearance %.2f m < %.1f m after every detour (walk %s vs wheel %s)" % (walk_clear, CLEARANCE_M, worst[1], o.name))
    rbx, rby = S[1]
    reeds = K.reed_bed(H, NAME + "_ReedBed", rbx, rby, 7.5, 5.0, h, SEED, W)
    rf_x, rf_y = site(ring([S[2], S[1], S[3]], (-14, -17, -20, -24, 14, 17, 20, 24)), clear=7)
    hut = K.refuge(H, NAME + "_Refuge", rf_x, rf_y, h(rf_x, rf_y), yaw + math.pi / 2)
    kp_x, kp_y = site(ring([S[1], S[0], S[2]], (9, 11, 13, -9, -11, -13)), max_slope=2.5)
    keeper = K.keeper_post(H, NAME + "_Keeper", kp_x, kp_y, h(kp_x, kp_y))
    sg_x, sg_y = at(BX, 10.5)                                 # beside the boardwalk bend, where the three ways part
    sign = K.signpost(H, NAME + "_Signpost", sg_x, sg_y, h(sg_x, sg_y),
                      [("repair", math.atan2(st_y - sg_y, st_x - sg_x)), ("harvest", math.atan2(rby - sg_y, rbx - sg_x)),
                       ("refuge", math.atan2(rf_y - sg_y, rf_x - sg_x))])
    # r2 dressing: each choice gets a ground pad, a pennant and its own material; the route gets lights and a stone edge
    hx_, hy_ = rbx + 10.5, rby                                # the reed drying rack (harvest)
    st_z, rf_z = h(st_x, st_y), h(rf_x, rf_y)
    station += K.choice_pad(H, NAME + "_Station", st_x, st_y, st_z, "repair") + K.awning(H, NAME + "_StationAwning", st_x, st_y, st_z, yaw + math.pi / 2, "repair")
    station += K.banner(H, NAME + "_StationBanner", st_x + px * 3.5, st_y + py * 3.5, h(st_x + px * 3.5, st_y + py * 3.5), "repair")
    reeds += K.choice_pad(H, NAME + "_Harvest", hx_, hy_, h(hx_, hy_), "harvest", 3.6) + K.banner(H, NAME + "_HarvestBanner", hx_ + 2.5, hy_ + 2.5, h(hx_ + 2.5, hy_ + 2.5), "harvest")
    hut += K.choice_pad(H, NAME + "_Refuge", rf_x, rf_y, rf_z - .4, "refuge", 5.2) + K.banner(H, NAME + "_RefugeBanner", rf_x - px * 5, rf_y - py * 5, h(rf_x - px * 5, rf_y - py * 5), "refuge")
    hut += K.reed_bed(H, NAME + "_RefugeReeds", *at(BX, -5.5), 3.0, 2.0, h, SEED + 1, W, count=40)
    hut += K.blossom_tree(H, NAME + "_RefugeBlossomA", rf_x + 6, rf_y + 4, h(rf_x + 6, rf_y + 4), SEED) + K.blossom_tree(H, NAME + "_RefugeBlossomB", rf_x - 5, rf_y + 6, h(rf_x - 5, rf_y + 6), SEED + 2)
    keeper += K.blossom_tree(H, NAME + "_KeeperBlossom", kp_x + 4, kp_y - 3, h(kp_x + 4, kp_y - 3), SEED + 3)
    shore_pts = lambda k: [at(S[i], k) for i in (1, 2, 3, 4)]
    shore = K.shore_stones(H, NAME + "_ShoreN", shore_pts(5.2), h, SEED, water_z=W) + K.shore_stones(H, NAME + "_ShoreS", shore_pts(-5.2), h, SEED + 5, water_z=W)
    walk += K.string_lights(H, NAME + "_Lights", route, h)
    # gameplay rows: what each piece is wired to, honestly
    X = []
    pu = chem["power_unit"]
    H.marker(X, NAME, "power_unit", "reed_wheel", wx, wy, W, "chemistry power_unit (drive the stream, salvageable); related source: tools/economy/colony_ledger.py Ledger.outfit",
             {"status": "design", "required_adapter": "a host-authoritative 'repair this wheel' action. Ledger.outfit(owner, deed, 'ENERGY', 'power_unit') only appends a generic ENERGY worker (PART_COST ENERGY iron 2 + copper 1); it is NOT a wheel repair (PootScoot 32427)",
              "pending": "wheel->machine wiring/snapping is design-only (island_chemistry power_unit.source; ADR-066 PowerUnit wiring)",
              "parts": sorted(pu["parts"]), "broken_paddles": 4, "rotor_pivot": "axle"})
    H.marker(X, NAME, "craft", "repair_station", st_x, st_y, h(st_x, st_y), "kit_waterworks.repair_station; part crates named by chemistry power_unit.parts",
             {"status": "design", "choice": "repair", "note": "salvage source exists: Ledger.hulks rotor salvage (colony_ledger.py:290)",
              "required_adapter": "a host-authoritative repair-station UI/action that takes power-unit parts and restores this wheel; no such action exists"})
    H.marker(X, NAME, "water", "reedbed_filter", rbx, rby, W, "chemistry water.filter_needed + spring_purity; voxel_aquatic USES purity bonus (FilterMoss +0.25 per plant)",
             {"status": "data", "purity": chem["water"]["spring_purity"], "filter_needed": chem["water"]["filter_needed"],
              "required_adapter": "a host purity state that reed planting raises and harvest lowers; today purity is rolled chemistry only",
              "design": "standing reeds raise purity; each harvest lowers it (no runtime yet)"})
    H.marker(X, NAME, "harvest", "reed_bed", rbx + 10.5, rby, h(rbx + 10.5, rby), "kit_waterworks.reed_bed drying rack",
             {"status": "design", "choice": "harvest", "note": "no reed item exists in data; no bag mutation is claimed",
              "required_adapter": "a reed item in the inventory catalog plus a host-authoritative harvest action that also lowers purity; neither exists"})
    H.marker(X, NAME, "refuge", "haven_hut", rf_x, rf_y, h(rf_x, rf_y), "design; related source: tools/economy/colony_ledger.py Ledger.settle_wave(held)",
             {"status": "design", "choice": "refuge",
              "required_adapter": "a host-authoritative shelter/occupancy model. settle_wave(held) counts zombies that FELL (and their drops), not sheltered occupants, so it does not model refuge (PootScoot 32427)"})
    H.marker(X, NAME, "npc", "npc_reed_keeper", kp_x, kp_y, h(kp_x, kp_y), "design: not in data/npcs/npcs.json",
             {"status": "design", "role": "ecology keeper"})
    H.marker(X, NAME, "quest_socket", "q_reedwheel_balance", kp_x + 1.4, kp_y, h(kp_x, kp_y), "design: proposed id, not in data/quests/quests.json",
             {"status": "design", "steps": ["talk npc_reed_keeper", "repair reed_wheel with bought parts", "leave reed_bed standing", "purity rises above 0.6"]},
             post=False)
    H.marker(X, NAME, "ecology", "reedbed_habitat", rbx, rby, W, "daedalus-core world/ecology Habitat/Ecosystem (Java)",
             {"status": "design", "related_source": "daedalus-core world/ecology Habitat/Ecosystem exist as code; binding this marker to a Habitat instance is host work", "fish": chem["water"]["fish"]}, post=False)
    H.marker(X, NAME, "walkway", "boardwalk", b0[0], b0[1], W + 1.0, "kit_waterworks.boardwalk + footbridge", {"status": "data", "note": "walkable; collision UCX_ boxes below"}, post=False)
    kit_posts = [o for o in H.GROUP[n0:] if o.name.startswith("MKR_")]
    # every kit object down by the deck datum, like the island
    shift(H.GROUP[n0:], -H.DECK)
    for r in X:
        r["world"] = list(r["local"])
    # collision (r3): UCX_<exact role mesh name>_NN, convex boxes, built in the island frame and re-based on the role
    # anchor exactly like the role mesh, so Unreal's FBX import pairs them and both share one origin
    hid = H.material("Collision", (1, 0, 1), 1)
    ucx = {k: [] for k in ("Walkway", "Refuge", "RepairStation")}

    def ucx_box(rk, center, size, rot_z=0.0):
        ob = H.box("UCX_%s_%s_%02d" % (NAME, rk, len(ucx[rk])), center, size, hid, 0, (0, 0, rot_z))
        ob.display_type, ob.hide_render = "WIRE", True
        ucx[rk].append(ob)
    pts = route + [b1]
    for a, b in zip(pts, pts[1:]):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        z = max(h(mx, my), W + .7) + .5 - H.DECK
        ucx_box("Walkway", (mx, my, z - .1), (math.hypot(b[0] - a[0], b[1] - a[1]), 2.4, .3), math.atan2(b[1] - a[1], b[0] - a[0]))
    ucx_box("Refuge", (rf_x, rf_y, rf_z + 1.4 - H.DECK), (6.6, 6.6, .3))                       # the hut floor
    ucx_box("RepairStation", (st_x, st_y, st_z + .1 - H.DECK), (7.6, 7.6, .25))                # the flagstone pad
    roles = {}
    dz = -H.DECK
    roles["WheelRotor"] = role(NAME + "_WheelRotor", rotor, (wx, wy, W + 3.4 - .7 + dz))
    roles["WheelFrame"] = role(NAME + "_WheelFrame", frame, (wx, wy, W + dz))
    roles["RepairStation"] = role(NAME + "_RepairStation", station, (st_x, st_y, h(st_x, st_y) + dz))
    roles["Walkway"] = role(NAME + "_Walkway", walk + bridge, (b0[0], b0[1], W + 1.0 + dz))
    roles["ReedBed"] = role(NAME + "_ReedBed", reeds, (rbx, rby, W + dz))
    roles["Refuge"] = role(NAME + "_Refuge", hut, (rf_x, rf_y, h(rf_x, rf_y) + dz))
    roles["KeeperPost"] = role(NAME + "_KeeperPost", keeper + sign, (kp_x, kp_y, h(kp_x, kp_y) + dz))
    roles["Shore"] = role(NAME + "_Shore", shore, (wx, wy, W + dz))
    # the clearance as delivered: final joined Walkway (planks, posts, rails, lights, bridge) against the final wheel
    bpy.context.view_layer.update()
    kd2 = __import__("mathutils").kdtree.KDTree(sum(len(roles[k].data.vertices) for k in ("WheelRotor", "WheelFrame")))
    n = 0
    for k in ("WheelRotor", "WheelFrame"):
        for v in roles[k].data.vertices:
            kd2.insert(roles[k].matrix_world @ v.co, n)
            n += 1
    kd2.balance()
    walk_clear = min(kd2.find(roles["Walkway"].matrix_world @ v.co)[2] for v in roles["Walkway"].data.vertices)
    if walk_clear < CLEARANCE_M:
        raise RuntimeError("delivered walk clearance %.3f m < %.1f m" % (walk_clear, CLEARANCE_M))
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    H.export_group(os.path.join(out_dir, NAME + "_Island"), island + kit_posts)
    files["Island"] = NAME + "_Island"
    for k, ob in roles.items():
        for u in ucx.get(k, []):                               # re-base each UCX on its role's anchor
            u.data.transform(u.matrix_basis)
            u.matrix_basis.identity()
            u.data.transform(__import__("mathutils").Matrix.Translation(-ob.location))
            u.location = ob.location.copy()
        H.export_group(os.path.join(out_dir, "%s_%s" % (NAME, k)), [ob] + ucx.get(k, []))
        files[k] = "%s_%s" % (NAME, k)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None
    layout = {
        "land_id": LAND_ID, "name": NAME, "seed": SEED, "kind": KIND, "realm": REALM, "not_a_deed": True,
        "units": "metres, Z up, +Y forward (FBX -Y forward/Z up; GLB Y-up)", "deck_datum_m": H.DECK, "water_m": H.WATER - H.DECK,
        "before": BEFORE, "story": dict(STORY, premise=STORY["premise"] % chem["water"]["spring_purity"]),
        "roles": {k: {"file": files[k] + ".glb", "fbx": files[k] + ".fbx", "anchor": [round(v, 3) for v in ob.location], "placement": "translate to anchor; orientation is baked in the island frame",
                      "pivot": "axle centre (spin about local axle)" if k == "WheelRotor" else "anchor",
                      "triangles": sum(len(p.vertices) - 2 for p in ob.data.polygons), "materials": [m.name for m in ob.data.materials if m],
                      "collision": [u.name for u in ucx.get(k, [])]}
                  for k, ob in roles.items()},
        "clearance": {"metric": "minimum 3-D distance between any Walkway vertex (boardwalk + footbridge) and any wheel vertex (rotor + frame), on final geometry",
                      "required_m": CLEARANCE_M, "measured_m": round(walk_clear, 3)},
        "bake_policy": "each role mesh and its UCX_<mesh>_NN share the anchor as object origin; vertices are island-frame minus anchor; place by translation only. Receiving qualification stays with the native operator.",
        "wheel": {"radius_m": 3.4, "width_m": 1.4, "paddles": 12, "broken_paddles": 4, "axle_yaw_rad": round(yaw + math.pi / 2, 4), "spin": "breastshot, top toward downstream"},
        "island": {k: man[k] for k in ("name", "terraces", "islet", "waterfall_lip", "lods", "triangles", "sockets", "outline")},
        "island_file": files["Island"] + ".glb",
        "gameplay": X + man["gameplay"],
        "chemistry": chem,
        "provenance": {"recipe": "tools/blender/reedwheel_haven.py + kit_waterworks.py + hd_island.py", "git": commit, "blender": bpy.app.version_string,
                       "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }
    for k in list(files):
        for ext in (".glb", ".fbx"):
            p = os.path.join(out_dir, files[k] + ext)
            if os.path.exists(p):
                layout.setdefault("hashes", {})[files[k] + ext] = [os.path.getsize(p), sha(p)]
    with open(os.path.join(out_dir, NAME + ".layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=1)
    pts = [r["anchor"] for k, r in layout["roles"].items()]
    focus = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))   # centroid of the haven's pieces
    spread = max(math.hypot(p[0] - focus[0], p[1] - focus[1]) for p in pts)
    # showcase cameras (land_showcase reads these): hero frames the wheel-water-refuge route, detail sits on the wheel
    layout["showcase"] = {"hero": [round(focus[0], 2), round(focus[1], 2), 0.0, round(spread * 2.9, 1)],
                          "detail": [round(wx, 2), round(wy, 2), round(W - H.DECK + 1.5, 2), 30.0]}
    with open(os.path.join(out_dir, NAME + ".layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=1)
    return layout, focus


def render(out_dir, focus):
    """Workbench previews (Blender renders, not Unreal captures): whole-island hero + top, and a haven close view."""
    H.render(out_dir, NAME, views=("hero", "top"))
    sc = bpy.context.scene
    cam = sc.camera
    fx, fy = focus
    cam.location = (fx + 38, fy - 34, 22)
    d = __import__("mathutils").Vector((fx, fy, -2)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out_dir, NAME + ".haven.png")
    bpy.ops.render.render(write_still=True)
    print("RENDER " + sc.render.filepath, flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = os.path.abspath(argv[0])
    t0 = time.time()
    lay, focus = build(out)
    print("REEDWHEEL %s roles=%d gameplay=%d %.0fs" % (lay["land_id"], len(lay["roles"]), len(lay["gameplay"]), time.time() - t0), flush=True)
    if "--render" in argv:
        render(out, focus)
