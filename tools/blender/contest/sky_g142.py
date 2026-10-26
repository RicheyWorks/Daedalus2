# SPDX-License-Identifier: MIT
"""G142 Sky-Crane Return: the release crate (pythagoras 50200, pyth-g142-assets-20261019; Daedalus2 main 10bd3a45), blender-kit/v1.
  Prop_Release_Crate_Closed / _Open   ~1.5 m tall aviary crate (0.8 x 1.0 m footprint) for one Mob_Sky_Crane: skids, floor, four posts,
          slatted sides and back (air gaps), plank roof, iron carry bars. The front door (-Y) is a named child <asset>_Door hinged on
          the left post; Open = swung out 110 deg. Same root pivot (bottom centre) in both states. UCX: walls / floor / roof on the
          root, one hull on the door.
  Prop_Release_Crate + Prop_Release_Crate_Door   the frame/mover split (UEB 48812): the door ships as its own glb, attached at the
          frame's SOCKET_Door (the hinge pivot); the open angle is in the frame's <asset>.sockets.json "hinges" (Blender euler + UE
          rotator). Frame sockets: SOCKET_Door, SOCKET_Crane (inside, floor centre: the crane's spawn), SOCKET_Release (outside the
          door, on the ground: where the crane steps out), SOCKET_Carry_L/R (carry bars).
The marsh / wetland reuse existing kits. Mob_Sky_Crane is crane_g142.py (bird_rig).
Usage: python sky_g142.py --out data/contest/sky_g142.kit.json"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K

SEED = 14243
BASE = "Prop_Release_Crate"
CW, CD, CH = 0.8, 1.0, 1.5
FLOOR = 0.12                                   # floor top
OPEN_DEG = -110                                # door swing about Z at the hinge (out to -Y, hinged on the -X post)
HINGE = (-CW / 2 + 0.03, -CD / 2, 0.0)
TIMBER, PLANK, IRON = "8A6A44", "A88A5E", "3A3A3E"
CAPS, SOCKETS = {}, {}
SPEC = {"gap": "G142", "ask": "pythagoras 50200", "lod": "LOD0/1", "size_m": "0.8 x 1.0 x 1.5 m aviary crate", "collision": "UCX walls/floor/roof + door",
        "states": ["Closed", "Open"], "code": "10bd3a45", "open_deg": abs(OPEN_DEG)}


def door_local():
    """door parts around the hinge (x from 0 at the hinge to the door width), closed pose."""
    W, H, z0 = CW - 0.08, CH - FLOOR - 0.06, FLOOR + 0.01; P = []
    for i, x in enumerate((0.03, W - 0.03)):
        P.append(K.box("Stile%d" % i, (0.05, 0.035, H), (x, 0, z0 + H / 2), 0, bevel=False))
    for i, z in enumerate((z0 + 0.03, z0 + H / 2, z0 + H - 0.03)):
        P.append(K.box("Rail%d" % i, (W, 0.035, 0.05), (W / 2, 0, z), 0, bevel=False))
    ang = math.degrees(math.atan2(H / 2 - 0.06, W - 0.1))
    for i, zc in enumerate((z0 + H / 4, z0 + 3 * H / 4)):
        P.append(K.box("Brace%d" % i, (math.hypot(W - 0.1, H / 2 - 0.06), 0.03, 0.045), (W / 2, -0.01, zc), 0, rot=(0, -ang, 0), bevel=False, lod1={"drop": True}))
    for i in range(5):                         # wire mesh bars in the upper panel (air + a view of the bird)
        P.append(K.box("Bar%d" % i, (0.008, 0.008, H / 2 - 0.08), (0.1 + i * (W - 0.2) / 4, 0.012, z0 + 3 * H / 4), 2, bevel=False, lod1={"drop": True}))
    P.append(K.box("Panel", (W - 0.06, 0.012, H / 2 - 0.06), (W / 2, 0.006, z0 + H / 4), 1, bevel=False))
    P.append(K.cyl("Handle", "z", 0.012, 0.012, 0.16, (W - 0.07, -0.04, z0 + H / 2), 2, 6, lod1={"segments": 4}))
    for i, z in enumerate((z0 + 0.15, z0 + H - 0.15)):
        P.append(K.box("Strap%d" % i, (0.14, 0.006, 0.03), (0.07, -0.02, z), 2, bevel=False, lod1={"drop": True}))
    return P


def place(local, deg):
    t = math.radians(deg); out = []
    for p in local:
        x, y, z = p["centre"]; q = dict(p)
        q["centre"] = [round(HINGE[0] + x * math.cos(t) - y * math.sin(t), 5), round(HINGE[1] + x * math.sin(t) + y * math.cos(t), 5), round(z, 5)]
        r = p.get("rot") or [0, 0, 0]
        if deg or p.get("rot"):
            q["rot"] = [r[0], r[1], round(r[2] + deg, 4)]
        out.append(q)
    return out


def crate(state, seed=SEED):
    a = BASE + "_" + state; op = state == "Open"; R = []
    for s in (-1, 1):
        R.append(K.box("Skid%s" % ("L" if s < 0 else "R"), (0.08, CD + 0.06, 0.08), (s * (CW / 2 - 0.06), 0, 0.04), 0, bevel=False))
    R.append(K.box("Floor", (CW, CD, 0.04), (0, 0, FLOOR - 0.02), 1, bevel=False))
    for sx in (-1, 1):
        for sy in (-1, 1):
            R.append(K.box("Post%d%d" % ((sx + 1) // 2, (sy + 1) // 2), (0.06, 0.06, CH - 0.08), (sx * (CW / 2 - 0.03), sy * (CD / 2 - 0.03), 0.08 + (CH - 0.08) / 2), 0, bevel=False))
    R.append(K.box("Roof", (CW + 0.06, CD + 0.06, 0.04), (0, 0, CH + 0.02), 1, bevel=False))
    for i in range(3):
        R.append(K.box("RoofBatten%d" % i, (CW + 0.06, 0.06, 0.03), (0, -CD / 2 + 0.06 + i * (CD - 0.12) / 2, CH + 0.055), 0, bevel=False, lod1={"drop": True}))
    n = 7; zs = [FLOOR + 0.06 + k * (CH - FLOOR - 0.14) / (n - 1) for k in range(n)]
    for k, z in enumerate(zs):                 # slatted walls with air gaps (LOD1 keeps every other slat)
        l1 = {"lod1": {"drop": True}} if k % 2 else {}
        for s in (-1, 1):
            R.append(K.box("Slat%s%d" % ("L" if s < 0 else "R", k), (0.02, CD - 0.08, 0.09), (s * (CW / 2 - 0.01), 0, z), 0, bevel=False, **l1))
        R.append(K.box("SlatB%d" % k, (CW - 0.08, 0.02, 0.09), (0, CD / 2 - 0.01, z), 0, bevel=False, **l1))
    for s in (-1, 1):
        R.append(K.cyl("CarryBar%s" % ("L" if s < 0 else "R"), "y", 0.018, 0.018, CD + 0.3, (s * (CW / 2 + 0.05), 0, 0.95), 2, 6, lod1={"segments": 4}))
        for sy in (-1, 1):
            R.append(K.box("BarBracket%s%d" % ("L" if s < 0 else "R", (sy + 1) // 2), (0.06, 0.03, 0.05), (s * (CW / 2 + 0.025), sy * (CD / 2 - 0.08), 0.95), 2, bevel=False, lod1={"drop": True}))
    D = place(door_local(), OPEN_DEG if op else 0)
    objs = [K.obj(a, R), K.obj(a + "_Door", D, parent=a, pivot=HINGE, role="door (hinge pivot, left front post)")]
    col = [K.ucx_box(a, 0, (0.03, CD, CH), (-CW / 2 + 0.015, 0, CH / 2)), K.ucx_box(a, 1, (0.03, CD, CH), (CW / 2 - 0.015, 0, CH / 2)),
           K.ucx_box(a, 2, (CW, 0.03, CH), (0, CD / 2 - 0.015, CH / 2)), K.ucx_box(a, 3, (CW, CD, FLOOR), (0, 0, FLOOR / 2)),
           K.ucx_box(a, 4, (CW + 0.06, CD + 0.06, 0.07), (0, 0, CH + 0.035))]
    dw = CW - 0.08; t = math.radians(OPEN_DEG if op else 0)
    dc = (HINGE[0] + dw / 2 * math.cos(t), HINGE[1] + dw / 2 * math.sin(t), FLOOR + (CH - FLOOR) / 2)
    col.append(dict(K.ucx_box(a, 5, (dw, 0.05, CH - FLOOR - 0.06), dc, parent=a + "_Door"), rot=[0, 0, OPEN_DEG if op else 0]))
    socks = [K.socket("Crane", (0, 0.05, FLOOR), forward=(0, -1, 0)), K.socket("Release", (0, -CD / 2 - 0.8, 0), forward=(0, -1, 0)),
             K.socket("Carry_L", (-(CW / 2 + 0.05), 0, 0.95), forward=(0, -1, 0)), K.socket("Carry_R", (CW / 2 + 0.05, 0, 0.95), forward=(0, -1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "state": state, "state_of": BASE, "spec": SPEC,
         "materials": [K.material(a, 0, "crate timber", TIMBER, 0.85), K.material(a, 1, "planks", PLANK, 0.85), K.material(a, 2, "iron fittings / mesh", IRON, 0.6, 0.6)],
         "objects": objs, "collision": col, "sockets": socks, "nanite": True}
    if op:
        m["off_centre_ok"] = "the open door swings out to -Y; root pivot stays the Closed crate's bottom centre so both states line up"
    CAPS[a] = 3000; SOCKETS[a] = [s["name"] for s in socks]
    return K.finish(m)


def door_socket(parts):
    """frame/mover split, then name the hinge SOCKET_Door (the ask) on the frame and in both hinge records."""
    out = []
    for m in parts:
        m = json.loads(json.dumps(m).replace("SOCKET_Hinge_Door", "SOCKET_Door").replace("SOCKET_Hinge_*", "SOCKET_Door"))
        m.pop("predicted", None); m = K.finish(m)
        SOCKETS[m["asset"]] = [s["name"] for s in m["sockets"]]
        out.append(m)
    return out


def assets(seed=SEED):
    c, o = crate("Closed", seed), crate("Open", seed)
    return [c, o] + door_socket(K.split_into(CAPS, SOCKETS, 3000, c, o))


def extra_checks(A):
    C, O, F, D = A[BASE + "_Closed"], A[BASE + "_Open"], A[BASE], A[BASE + "_Door"]
    fs = {s["name"]: s["location"] for s in F["sockets"]}
    h = F["hinges"][0]
    return [("crate ~1.5 m tall, 0.8 x 1.0 m footprint", abs(C["predicted"]["dimensions"][2] - 1.575) < 0.03 and C["predicted"]["dimensions"][0] < 1.0, C["predicted"]["dimensions"]),
            ("crane (1.18 m) fits inside under the roof", CH - FLOOR > 1.25),
            ("states share nodes, pivots, sockets and tris", [o["pivot"] for o in O["objects"]] == [o["pivot"] for o in C["objects"]] and O["sockets"] == C["sockets"] and O["predicted"]["triangles"] == C["predicted"]["triangles"]),
            ("door is a named child with its own UCX", C["objects"][1]["name"] == C["asset"] + "_Door" and sum(1 for c in C["collision"] if c["parent"] == C["asset"] + "_Door") == 1),
            ("frame: SOCKET_Door at the hinge pivot + crane/release/carry", set(fs) == {"SOCKET_Door", "SOCKET_Crane", "SOCKET_Release", "SOCKET_Carry_L", "SOCKET_Carry_R"} and fs["SOCKET_Door"] == [round(v, 5) for v in HINGE]),
            ("open angle in the hinge record (sidecar): 110 deg about Z", h["socket"] == "SOCKET_Door" and h["open_blender_euler_deg"] == [0, 0, OPEN_DEG] and h["open_ue_rotator"] is not None, h),
            ("door mover origin = hinge pivot, hinge named SOCKET_Door", D["hinge"]["socket"] == "SOCKET_Door" and D["hinge"]["pivot_m"] == list(HINGE)),
            ("release point outside the open door's sweep", fs["SOCKET_Release"][1] < -CD / 2 - (CW - 0.08))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
