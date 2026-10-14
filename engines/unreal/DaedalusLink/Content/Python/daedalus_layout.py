# SPDX-License-Identifier: MIT
"""Pack the team (NFT) islands next to each other (Richey 2026-10-13: "the nft islands all need to be right next to
each other", "they are to spread out"). Some sat 20-60 km apart; this lays them out in rows with a fixed gap, north
of World Zero's island lane and away from the gate row in the south.

    import daedalus_layout
    daedalus_layout.plan()          # dry run: every island level, its footprint, where it would go
    daedalus_layout.apply()         # move them, save the levels, write the undo table
    daedalus_layout.undo(path)      # put them back from an undo table

Each island is a streaming sublevel; the whole level moves by one offset (every root actor; attached actors ride
along), so its own layout is untouched and its height is kept. The footprint is the dense cluster of the level's
actors (within CLUSTER_CM of their median), so a stray far-away actor can't inflate it. Pure packing is in pack(),
tested by test_daedalus_layout.py without the editor.
"""
import json
import os
import time

GAP_CM = 6000.0          # 60 m of open sky between neighbouring islands
ROW_CM = 180000.0        # a row is at most 1.8 km wide before the next row starts
ORIGIN = (-20000.0, 18000.0)   # first row's west edge and south edge: north of the lane and the Daedalus hub
CLUSTER_CM = 200000.0    # actors within 2 km of the median make the footprint
SKIP_LEVELS = {"DaedalusWorld"}   # the persistent level (World Zero, gates, hub) stays where it is


def pack(boxes, gap=GAP_CM, row=ROW_CM, origin=ORIGIN):
    """boxes: [(name, width, depth)] in cm. Returns {name: (cx, cy)} target centres, shelf-packed: tallest first,
    left to right, a new row when the row would pass `row`. Deterministic (ties by name)."""
    order = sorted(boxes, key=lambda b: (-b[2], -b[1], b[0]))
    x0, y0 = origin
    x, y, row_depth = x0, y0, 0.0
    out = {}
    for name, w, d in order:
        if x > x0 and x + w > x0 + row:
            x, y, row_depth = x0, y + row_depth + gap, 0.0
        out[name] = (x + w / 2.0, y + d / 2.0)
        x += w + gap
        row_depth = max(row_depth, d)
    return out


def groups(rows, gap=GAP_CM):
    """rows: {level: (cx, cy, w, d)}. Levels whose footprints touch (within one gap) are one island and move
    together (AMF's pets level sits on AMF's island). Returns {group name: (members, (cx, cy, w, d))}."""
    names = sorted(rows)
    parent = {n: n for n in names}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def box(n):
        cx, cy, w, d = rows[n]
        return cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = box(a), box(b)
            if A[0] - gap < B[2] and B[0] - gap < A[2] and A[1] - gap < B[3] and B[1] - gap < A[3]:
                parent[find(a)] = find(b)
    out = {}
    for n in names:
        out.setdefault(find(n), []).append(n)
    res = {}
    for members in out.values():
        bs = [box(m) for m in members]
        x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
        x1, y1 = max(b[2] for b in bs), max(b[3] for b in bs)
        res["+".join(members)] = (members, ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    return res


def hub_cells(hub_w, hub_d, pitch_m=None, margin_m=40.0):
    """Cells the hub island (the persistent level) covers, centred on the hub cell: reserved before any estate is
    placed. hub_w/hub_d in cm."""
    import daedalus_land_grid as G
    pitch = pitch_m or G.PITCH_M
    half_w = (hub_w / 100.0) / 2.0 + margin_m
    half_d = (hub_d / 100.0) / 2.0 + margin_m
    out = set()
    for x in range(G.SIDE):
        for y in range(G.SIDE):
            mx, my = (x - G.HUB) * pitch, (y - G.HUB) * pitch
            if abs(mx) <= half_w + pitch / 2.0 and abs(my) <= half_d + pitch / 2.0:
                out.add((x, y))
    return frozenset(out)


def spiral_targets(boxes, hub_cm, hub_size_cm, pitch_m=None):
    """ADR-065 placement (Richey 2026-10-13: 'why are the islands so far apart'): each island group becomes the
    lowest-numbered free estate that fits it, spiralling out from the hub. boxes: [(name, w, d)] in cm; hub_cm the
    hub island's centre in world cm; hub_size_cm its (w, d). Returns {name: {"to": (cx, cy) cm, "cell": (x, y),
    "size": s, "deed": n}}. Pure: test_daedalus_layout.py proves no overlap and no split district."""
    import daedalus_land_grid as G
    pitch = pitch_m or G.PITCH_M
    sizes = {name: G.size_for(w / 100.0, d / 100.0, pitch) for name, w, d in boxes}
    taken = hub_cells(hub_size_cm[0], hub_size_cm[1], pitch)
    placed = G.place_estates(sizes, taken)
    out = {}
    for name, (x, y, s, deed) in placed.items():
        mx, my = G.estate_centre_m(x, y, s, pitch)
        out[name] = {"to": (hub_cm[0] + mx * 100.0, hub_cm[1] + my * 100.0), "cell": (x, y), "size": s, "deed": deed}
    return out


def _median(v):
    s = sorted(v)
    return s[len(s) // 2] if s else 0.0


def footprint(points):
    """points: [(x, y, ex, ey)] actor centres and half-extents. (cx, cy, w, d) of the dense cluster."""
    mx, my = _median([p[0] for p in points]), _median([p[1] for p in points])
    near = [p for p in points if abs(p[0] - mx) < CLUSTER_CM and abs(p[1] - my) < CLUSTER_CM] or points
    x0 = min(p[0] - p[2] for p in near)
    x1 = max(p[0] + p[2] for p in near)
    y0 = min(p[1] - p[3] for p in near)
    y1 = max(p[1] + p[3] for p in near)
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0, x1 - x0, y1 - y0


# ---- editor side ----------------------------------------------------------------------------------------------

def _levels():
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {}
    for a in sub.get_all_level_actors():
        lv = a.get_level().get_outer().get_name()
        if lv in SKIP_LEVELS:
            continue
        by.setdefault(lv, []).append(a)
    return by


def _roots(actors):
    return [a for a in actors if a.get_attach_parent_actor() is None]


def plan():
    import unreal  # noqa: F401
    rows = {}
    for lv, actors in _levels().items():
        pts = []
        for a in actors:
            o, e = a.get_actor_bounds(False)
            if e.x == 0 and e.y == 0:
                o, e = a.get_actor_location(), type(o)(0, 0, 0)
            if e.x > 50000 or e.y > 50000:      # sky domes, huge volumes: not the island's ground
                continue
            pts.append((o.x, o.y, e.x, e.y))
        if pts:
            rows[lv] = footprint(pts)
    gs = groups(rows)
    target = pack([(g, f[2], f[3]) for g, (_, f) in gs.items()])
    out = []
    for g, (members, (cx, cy, w, d)) in sorted(gs.items()):
        tx, ty = target[g]
        for lv in members:
            out.append({"level": lv, "group": g, "from": [round(cx), round(cy)], "to": [round(tx), round(ty)],
                        "size_m": [round(w / 100), round(d / 100)], "move": [round(tx - cx), round(ty - cy)]})
    return out


def _hub():
    """(centre cm, (w, d) cm) of the persistent level's island: the spiral's hub cell."""
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    pts = []
    for a in sub.get_all_level_actors():
        if a.get_level().get_outer().get_name() not in SKIP_LEVELS:
            continue
        o, e = a.get_actor_bounds(False)
        if e.x == 0 and e.y == 0:
            o, e = a.get_actor_location(), type(o)(0, 0, 0)
        if e.x > 50000 or e.y > 50000:
            continue
        pts.append((o.x, o.y, e.x, e.y))
    cx, cy, w, d = footprint(pts) if pts else (0.0, 0.0, 0.0, 0.0)
    return (cx, cy), (w, d)


def _rows():
    import unreal  # noqa: F401
    rows = {}
    for lv, actors in _levels().items():
        pts = []
        for a in actors:
            o, e = a.get_actor_bounds(False)
            if e.x == 0 and e.y == 0:
                o, e = a.get_actor_location(), type(o)(0, 0, 0)
            if e.x > 50000 or e.y > 50000:
                continue
            pts.append((o.x, o.y, e.x, e.y))
        if pts:
            rows[lv] = footprint(pts)
    return rows


def spiral_plan():
    """Dry run of the ADR-065 placement: every island group, its estate (cell, size, deed) and the move."""
    hub_cm, hub_size = _hub()
    gs = groups(_rows())
    target = spiral_targets([(g, f[2], f[3]) for g, (_, f) in gs.items()], hub_cm, hub_size)
    out = []
    for g, (members, (cx, cy, w, d)) in sorted(gs.items()):
        t = target[g]
        tx, ty = t["to"]
        for lv in members:
            out.append({"level": lv, "group": g, "from": [round(cx), round(cy)], "to": [round(tx), round(ty)],
                        "size_m": [round(w / 100), round(d / 100)], "move": [round(tx - cx), round(ty - cy)],
                        "cell": list(t["cell"]), "estate": t["size"], "deed": t["deed"]})
    return {"hub": [round(hub_cm[0]), round(hub_cm[1])], "hub_size_m": [round(hub_size[0] / 100), round(hub_size[1] / 100)], "plan": out}


def spiral_apply():
    """Move every island onto its estate, save, write the undo table (undo(path) puts them back)."""
    import unreal
    sp = spiral_plan()
    p = sp["plan"]
    moves = {r["level"]: (float(r["move"][0]), float(r["move"][1])) for r in p}
    n = _move(moves)
    path = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Daedalus",
                        time.strftime("layout-undo-spiral-%m%d-%H%M%S.json"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"plan": sp, "undo": {lv: [-dx, -dy] for lv, (dx, dy) in moves.items()}}, f, indent=1)
    return {"levels": len(p), "actors_moved": n, "undo": path, "hub": sp["hub"], "plan": p}


def _move(level_moves):
    import unreal
    by = _levels()
    moved = 0
    for lv, (dx, dy) in level_moves.items():
        for a in _roots(by.get(lv, [])):
            a.set_actor_location(a.get_actor_location() + unreal.Vector(dx, dy, 0.0), False, False)
            moved += 1
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return moved


def apply():
    import unreal
    p = plan()
    moves = {r["level"]: (float(r["move"][0]), float(r["move"][1])) for r in p}
    n = _move(moves)
    path = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Daedalus",
                        time.strftime("layout-undo-%m%d-%H%M%S.json"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"plan": p, "undo": {lv: [-dx, -dy] for lv, (dx, dy) in moves.items()}}, f, indent=1)
    return {"levels": len(p), "actors_moved": n, "undo": path, "plan": p}


def undo(path):
    with open(path) as f:
        u = json.load(f)["undo"]
    return {"actors_moved": _move({lv: (d[0], d[1]) for lv, d in u.items()})}
