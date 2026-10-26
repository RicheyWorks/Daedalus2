# SPDX-License-Identifier: MIT
"""Contest row 13 (G13 living painting; buffffff 48312), blender-kit/v1.
Prop_Gal_LivingFrame_{Faded,Half,Restored}  2 x 1.5 m gilded frame on the wall; the painting is the child node
    Prop_Gal_LivingFrame_<State>_Canvas (sky, hills, sun: 3 slots). The states share mesh, pivot and sockets; only the canvas
    colours change (faded = 85 % toward dull parchment, half = 45 %, restored = full colour, sun glows). SOCKET_Canvas at the
    canvas centre front, SOCKET_Light for a picture light above. UCX slab. Origin bottom centre; hangs on a wall at Blender +Y.
REUSE check: no Gallery (Gal) frames exist in catalog.bba or art\\glb (Item_Part_Frame_* are crafting parts) -> new.
Usage: python gal_frame.py --out data/contest/gal_frame.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1313
FR = "Prop_Gal_LivingFrame"
STATES = {"Faded": 0.85, "Half": 0.45, "Restored": 0.0}
VIVID = {"sky": "5FA8E0", "land": "4E9A3E", "sun": "F2C744"}
DULL = "B9AE96"
CAPS = {"%s_%s" % (FR, s): 3000 for s in STATES}
SOCKETS = {"%s_%s" % (FR, s): ["SOCKET_Canvas", "SOCKET_Light"] for s in STATES}


def mix(h1, h2, t):
    a = [int(h1[i:i + 2], 16) for i in (0, 2, 4)]; b = [int(h2[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join("%02X" % int(round(x + (y - x) * t)) for x, y in zip(a, b))


def frame(state, seed=SEED):
    a = "%s_%s" % (FR, state); f = STATES[state]; cv = a + "_Canvas"; r = K.rng(seed, FR)
    mats = [K.material(a, 0, "gilded frame", "B8923A", 0.45, 0.7), K.material(a, 1, "dark backing", "3B2A1E", 0.9),
            K.material(a, 2, "sky", mix(VIVID["sky"], DULL, f), 0.9), K.material(a, 3, "hills", mix(VIVID["land"], DULL, f), 0.9),
            K.material(a, 4, "sun", mix(VIVID["sun"], DULL, f), 0.6, 0.0, glow=state == "Restored")]
    F = K.plain_lod1(K.box("RailT", (2.0, 0.08, 0.12), (0, 0, 1.44), 0)) + K.plain_lod1(K.box("RailB", (2.0, 0.08, 0.12), (0, 0, 0.06), 0)) + \
        K.plain_lod1(K.box("RailL", (0.12, 0.08, 1.26), (-0.94, 0, 0.75), 0)) + K.plain_lod1(K.box("RailR", (0.12, 0.08, 1.26), (0.94, 0, 0.75), 0)) + \
        [K.box("Backing", (1.8, 0.02, 1.3), (0, 0.03, 0.75), 1, bevel=False)]
    for i, (x, z) in enumerate([(-0.94, 1.44), (0.94, 1.44), (-0.94, 0.06), (0.94, 0.06)]):
        F += K.plain_lod1(K.box("Rosette%d" % i, (0.12, 0.1, 0.12), (x, -0.01, z), 0))
    C = [K.box("Sky", (1.76, 0.01, 1.26), (0, 0.015, 0.75), 2, bevel=False)]
    C.append(K.box("Meadow", (1.76, 0.008, 0.2), (0, 0.004, 0.22), 3, bevel=False))   # covers the corners the tilted hills leave open
    for i in range(3):                                            # seeded rolling hills: tilted slabs in front of the sky
        w = r.uniform(0.7, 1.1); x = -0.55 + 0.55 * i + r.uniform(-0.08, 0.08); tilt = r.uniform(-14, 14)
        C.append(K.box("Hill%d" % i, (round(w, 4), 0.008, 0.42), (round(max(-0.88 + w / 2, min(0.88 - w / 2, x)), 5), 0.006 - 0.002 * i, round(0.31 + 0.05 * i, 5)), 3,
                       rot=(0, round(tilt, 3), 0), bevel=False))
    C.append(K.cyl("Sun", "y", 0.13, 0.13, 0.008, (0.5, 0.004, 1.12), 4, 16, lod1={"segments": 8}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "state": state, "state_of": FR, "fade": f,
         "spec": {"row": 13, "gap": "G13", "size_m": "2 x 1.5 m frame", "tri_cap": 3000, "lod": "LOD0/1", "collision": "UCX slab", "sockets": ["Canvas", "Light"],
                  "states": list(STATES)}, "materials": mats,
         "objects": [K.obj(a, F), K.obj(cv, C, parent=a, pivot=(0, 0, 0), role="canvas (painting; colours change per state)")],
         "sockets": [K.socket("Canvas", (0, -0.03, 0.75)), K.socket("Light", (0, -0.25, 1.6))],
         "collision": [K.ucx_box(a, 0, (2.0, 0.1, 1.5), (0, 0, 0.75))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [frame(s, seed) for s in STATES]


def extra_checks(A):
    S = [A["%s_%s" % (FR, s)] for s in STATES]
    return [("frame 2 x 1.5 m", all(abs(m["predicted"]["dimensions"][0] - 2.0) < 0.01 and abs(m["predicted"]["dimensions"][2] - 1.5) < 0.01 for m in S), S[0]["predicted"]["dimensions"]),
            ("states share mesh, pivot, sockets", len({m["predicted"]["triangles"] for m in S}) == 1 and all(m["sockets"] == S[0]["sockets"] for m in S)),
            ("colours wake up faded -> half -> restored", [m["fade"] for m in S] == [0.85, 0.45, 0.0] and S[2]["materials"][2]["hex"] == VIVID["sky"]),
            ("only the restored sun glows", [m["materials"][4]["glow"] for m in S] == [False, False, True]),
            ("canvas child has <= 3 slots", len({p["slot"] for p in S[0]["objects"][1]["parts"]}) <= 3)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
