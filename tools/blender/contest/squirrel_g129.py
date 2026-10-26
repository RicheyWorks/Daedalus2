# SPDX-License-Identifier: MIT
"""G129 Squirrel's Winter: Pip the red squirrel (pythagoras 50065, pyth-g129-assets-20261019; code 6df61143 PatchForager / FORAGE01).
  Mob_Red_Squirrel  ~40 cm nose to tail tip (~22 cm body + ~19 cm bushy tail), skinned: the reusable tools/blender/creatures/
                    quadruped_rig.py recipe with body params (short legs, upright ears + eyes, paws, no back plates) and its bushy
                    tail extension (3 tail bones curling up over the back). Clips Idle / Run / Forage (Forage = sitting up on the
                    haunches, forepaws at the mouth, nibbling: the per-patch picking loop). Rigid bind (small, faceted parts).
                    Pinned at data/contest/g129_squirrel.quad.json, built by creatures/build_quadruped.py. No sockets, no sidecar.
Usage: python squirrel_g129.py --out data/contest/g129_squirrel.quad.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures"))
import kitlib as K
import quadruped_rig as Q

SEED = 12906
ASSET = "Mob_Red_Squirrel"
SCALE = 0.265                                  # quadruped_rig length param; nose-to-rump ~0.83 x SCALE = ~0.22 m
BODY = {"body_h": 0.3, "body_w": 0.26, "leg": 0.2, "plates": 0, "tail": 0.72, "head_lift": 0.06, "ornament": "ears", "ear": 0.14,
        "tail_bones": 3, "tail_bush": 0.16, "tail_curl": 110.0, "feet": "paw"}
CLIPS = ("Idle", "Run", "Forage")
SPEC = {"gap": "G129", "size_m": "~0.4 m nose to tail tip incl. bushy tail", "tri_cap": 6000, "lod": "LOD0/1", "collision": "none (capsule in UE)",
        "rig": "skinned rigid; quadruped_rig + bushy tail (Tail, Tail1, Tail2); clips Idle, Run, Forage", "asker": "pythagoras 50065",
        "forage": "Forage = sit up on the haunches, forepaws at the mouth, nibbling (loop while picking a patch; leave at the theta rule)"}


def squirrel(seed=SEED):
    mats = [K.material(ASSET, 0, "red squirrel fur", "B4552A", 0.9), K.material(ASSET, 1, "eye black", "1C1410", 0.4),
            K.material(ASSET, 2, "paw dark", "4A2E20", 0.85)]
    return Q.recipe(ASSET, seed, SCALE, materials=mats, spec=SPEC, body=BODY, clip_names=CLIPS, bind_mode="rigid")


def length_nose_to_tail(m):
    """Nose (front of the head) to the tail tip measured along the body and the tail chain (the tail curls up, so bounds understate it)."""
    nose = min(p["centre"][1] - p["size"][1] / 2 for p in m["parts"] if p["shape"] == "box" and p["bone"] == "Head")
    B = {b["name"]: b for b in m["bones"]}; L = m["params"]["length"]
    chain = sum(sum((B[n]["tail"][k] - B[n]["head"][k]) ** 2 for k in range(3)) ** 0.5 for n in B if n.startswith("Tail"))
    return round((0.33 * L - nose) + chain, 4)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    m = squirrel(o.seed)
    with open(o.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    p = m["predicted"]; print(o.out, p["triangles"], p["lod1_triangles"], p["lod1_ratio"], p["dimensions"], p["bounds_min"], "nose-to-tail", length_nose_to_tail(m))
