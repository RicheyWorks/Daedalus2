# SPDX-License-Identifier: MIT
"""G58 Trophic Cascade elk placeholder (pythagoras 49460 re 49357, pyth-g58-assets-20261019; code 1b2ce07f TrophicCascade).
  Mob_Valley_Elk  ~2.2 m long antlered grazer, skinned: the same reusable tools/blender/creatures/quadruped_rig.py recipe as
                  Mob_Lab_Hornback (15 bones, baked Idle / Walk / Run), with body params (taller legs, slimmer body, lifted neck,
                  short tail, no back plates) and the rig module's antler generator. Pinned at data/contest/g58_elk.quad.json,
                  built by creatures/build_quadruped.py. No sockets (bone attach in UE), so no sidecar. Placeholder: Mob_Lab_Hornback
                  stands in until this is accepted.
Usage: python g58_elk.py --out data/contest/g58_elk.quad.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures"))
import kitlib as K
import quadruped_rig as Q

SEED = 5859
ELK = "Mob_Valley_Elk"
SCALE = 2.56                                   # quadruped_rig length param; nose-to-tail ~0.86 x SCALE = ~2.2 m
BODY = {"body_h": 0.2, "body_w": 0.19, "leg": 0.46, "plates": 0, "tail": 0.06, "head_lift": 0.1, "ornament": "antlers", "antler": 0.21}
SPEC = {"gap": "G58", "size_m": "~2.2 m long, antlered", "tri_cap": 6000, "lod": "LOD0/1", "collision": "none (capsule in UE)",
        "rig": "skinned; baked Idle, Walk, Run (quadruped_rig, as Mob_Lab_Hornback)", "asker": "pythagoras 49460", "placeholder": True}


def elk(seed=SEED):
    mats = [K.material(ELK, 0, "elk hide", "6B4A32", 0.9), K.material(ELK, 1, "antler bone", "C9B48E", 0.75), K.material(ELK, 2, "hoof", "2E2622", 0.8)]
    return Q.recipe(ELK, seed, SCALE, materials=mats, spec=SPEC, body=BODY)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    m = elk(o.seed)
    with open(o.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    p = m["predicted"]; print(o.out, p["triangles"], p["lod1_triangles"], p["lod1_ratio"], p["dimensions"], p["bounds_min"], m["params"]["tines"], m["params"]["antler"])
