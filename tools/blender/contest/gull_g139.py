# SPDX-License-Identifier: MIT
"""G139 Char_YTM_Gull (youtube-master 50117, PR #360 HarbourRound: "a gull flock that grows louder on clashes"): the first use of the
reusable creatures/bird_rig.py (blender-bird/v1), built by creatures/build_quadruped.py; pinned at data/contest/g139_gull.quad.json.
PR #360 has no pose enum, so "idle and squawk poses" ship as baked looping clips Idle and Squawk (a flock plays Squawk more often
as clashes rise). ~0.6 m herring gull, 10 bones, rigid parts. Usage: python gull_g139.py --out data/contest/g139_gull.quad.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "creatures")); sys.path.insert(0, os.path.join(HERE, "..", "kit"))
import bird_rig as R
SEED, GULL = 13939, "Char_YTM_Gull"
SPEC = {"gap": "G139", "ask": "youtube-master 50117", "size_m": "0.6 m beak to tail", "clips": ["Idle", "Squawk"], "rig": "bird_rig blender-bird/v1"}


def gull(seed=SEED):
    return R.recipe(GULL, seed, spec=SPEC)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    m = gull(o.seed)
    with open(o.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    p = m["predicted"]; print(o.out, p["triangles"], p["lod1_triangles"], p["lod1_ratio"], p["dimensions"], p["bounds_min"])
