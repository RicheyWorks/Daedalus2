# SPDX-License-Identifier: MIT
"""G58 Trophic Cascade fence (pythagoras 49257, pyth-g58-assets-20261019; code main 1b2ce07f battlefield.TrophicCascade.fence(reach)), blender-kit/v1.
Prop_Valley_ExclosureFence          tileable 3 m willow exclosure segment, 1.8 m tall: round timber posts at x=-1.5 (joint) and x=0,
                                    8 high-tensile strands (closer near the ground) + vertical stay wires every 0.3 m. The segment owns
                                    only its -X joint post, so chained segments share posts (one every 1.5 m).
Prop_Valley_ExclosureFence_EndPost  the post (with a ground brace) that closes the +X end of a run.
Chaining: SOCKET_End_A (-X, x=-1.5) and SOCKET_End_B (+X, x=+1.5) at ground level; segment n End_B = segment n+1 End_A;
the EndPost's SOCKET_End_A goes on the last segment's End_B. UCX: one wall per segment (keeps elk and deer out).
REUSE check: Prop_BUF_Fence_V1-V12 (buffffff) are 2.1 x 1.45 m timber rail fences, no wire, no sockets; Prop_Live_AMF_Fence_V1-V20
(art-master-flex) are 1.1 x 1.0 m; Prop_YTM_Fence_V1-V4 are 1.5 m placeholders -> none is a 3 x 1.8 m post-and-wire exclosure, so new.
Wolf / elk / willow are reused, not built here (see the G58 DONE).
Usage: python valley_g58.py --out data/contest/valley_g58.kit.json"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 5858
FENCE, END = "Prop_Valley_ExclosureFence", "Prop_Valley_ExclosureFence_EndPost"
CAPS = {FENCE: 2500, END: 600}
SOCKETS = {FENCE: ["SOCKET_End_A", "SOCKET_End_B"], END: ["SOCKET_End_A"]}
SPEC = {"gap": "G58", "ask": "pythagoras 49257", "lod": "LOD0/1"}
W, H, POST_H, POST_R = 3.0, 1.8, 1.9, 0.06
STRANDS = [0.12, 0.27, 0.45, 0.66, 0.9, 1.17, 1.47, 1.78]
STAYS = [round(-1.5 + 0.3 * i, 4) for i in range(1, 10) if abs(-1.5 + 0.3 * i) > 1e-9]


def mats(a):
    return [K.material(a, 0, "weathered post timber", "6F5B45", 0.9), K.material(a, 1, "galvanised wire", "9EA3A8", 0.45, metallic=0.8), K.material(a, 2, "post cap / staples", "4A3D30", 0.85)]


def post(nm, x, h=POST_H, r=POST_R):
    return [K.cyl(nm, "z", r, r * 0.92, h, (x, 0, h / 2), 0, 8, lod1={"segments": 5}),
            K.cyl(nm + "_Cap", "z", r * 1.05, r * 0.4, 0.05, (x, 0, h + 0.025), 2, 8, lod1={"drop": True})]


def fence(seed=SEED):
    a = FENCE
    P = post("PostJoint", -W / 2) + post("PostMid", 0)
    for i, z in enumerate(STRANDS):
        P.append(K.cyl("Strand%d" % i, "x", 0.004, 0.004, W, (0, -POST_R - 0.004, z), 1, 4, lod1=None if i % 2 == 0 else {"drop": True}))
    for i, x in enumerate(STAYS):
        P.append(K.cyl("Stay%d" % i, "z", 0.003, 0.003, STRANDS[-1] - STRANDS[0], (x, -POST_R - 0.008, (STRANDS[0] + STRANDS[-1]) / 2), 1, 4, lod1=None if i % 2 == 0 else {"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="3 m x 1.8 m wire (posts 1.9 m), tileable", tri_cap=2500, collision="UCX wall", sockets=["End_A", "End_B"],
         chain="segment n SOCKET_End_B = segment n+1 SOCKET_End_A; close a run with %s" % END),
         "materials": mats(a), "objects": [K.obj(a, P)], "sockets": [K.socket("End_A", (-W / 2, 0, 0), forward=(-1, 0, 0)), K.socket("End_B", (W / 2, 0, 0), forward=(1, 0, 0))],
         "collision": [K.ucx_box(a, 0, (W, 0.14, H), (0, 0, H / 2))], "nanite": True}
    return K.finish(m)


def endpost(seed=SEED):
    a = END
    P = post("Post", 0, POST_H + 0.05, POST_R * 1.15)
    P.append(K.cyl("Brace", "x", 0.04, 0.04, 1.2, (-0.42, 0, 0.55), 0, 6, rot=(0, -52, 0), lod1={"segments": 4}))
    P.append(K.box("BracePad", (0.18, 0.12, 0.04), (-0.8, 0, 0.02), 2, bevel=False))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="end post 1.95 m + brace", tri_cap=600, collision="UCX post", sockets=["End_A"]),
         "materials": mats(a), "objects": [K.obj(a, P)], "sockets": [K.socket("End_A", (0, 0, 0), forward=(-1, 0, 0))],
         "collision": [K.ucx_box(a, 0, (0.15, 0.15, POST_H), (0, 0, POST_H / 2))],
         "off_centre_ok": "brace runs back along the fence (-X) from the post; origin = post so SOCKET_End_A sits on the run's end", "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [fence(seed), endpost(seed)]


def extra_checks(A):
    F = A[FENCE]; s = {x["name"]: x["location"] for x in F["sockets"]}
    return [("segment ~3 m wide", abs(s["SOCKET_End_B"][0] - s["SOCKET_End_A"][0] - 3.0) < 1e-9),
            ("wire 1.8 m tall", abs(STRANDS[-1] - 1.8) < 0.03 and abs(F["collision"][0]["size"][2] - 1.8) < 1e-9),
            ("tileable: only the -X joint post (shared when chained)", sum(1 for q in F["objects"][0]["parts"] if q["name"] in ("PostJoint", "PostMid")) == 2 and
             not any(q["name"].startswith("Post") and q["centre"][0] > 1.0 for q in F["objects"][0]["parts"])),
            ("strands span exactly End_A..End_B", all(abs(q["length"] - 3.0) < 1e-9 for q in F["objects"][0]["parts"] if q["name"].startswith("Strand"))),
            ("sockets at ground level", all(v[2] == 0 for v in s.values()))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
