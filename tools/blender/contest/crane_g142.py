# SPDX-License-Identifier: MIT
"""G142 Sky-Crane Return: the sky crane (pythagoras 50200, pyth-g142-assets-20261019; Daedalus2 main 10bd3a45).
  Mob_Sky_Crane  ~1.2 m tall long-legged crane on the reusable creatures/bird_rig.py (blender-bird/v1, first built for the G139 gull)
                 with long-bird body params (leg_frac 0.5, slim neck, small head, long beak). Clips Idle / Walk / Fly / Dance
                 (Dance = the courtship hop with the wings half open, bowing between hops). Rigid bind.
                 SOCKET_LegBand on bone Leg_L (lower leg, ~30 % of the leg height up from the foot), rotation [0, 0, 0] (Z up the leg):
                 G163 Prop_Leg_Band attaches here (its origin = the band centre, hole axis Z). Pinned at data/contest/g142_crane.quad.json.
Usage: python crane_g142.py --out data/contest/g142_crane.quad.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures"))
import kitlib as K
import bird_rig as R

SEED = 14242
ASSET = "Mob_Sky_Crane"
BODY = {"length": 1.0, "height_frac": 1.2, "leg_frac": 0.5, "neck_r": 0.55, "head_scale": 0.7, "wing_lift_deg": 30.0, "tail_off": 0.07}
CLIPS = ("Idle", "Walk", "Fly", "Dance")
BAND_UP = 0.3                       # band height as a fraction of the leg (hip height) above the foot
SPEC = {"gap": "G142", "size_m": "~1.2 m tall", "tri_cap": 6000, "lod": "LOD0/1", "collision": "capsule in UE", "asker": "pythagoras 50200",
        "rig": "blender-bird/v1 (bird_rig.py), rigid; clips Idle, Walk, Fly, Dance", "sockets": "SOCKET_LegBand on Leg_L (G163 Prop_Leg_Band)"}


def band_location(P):
    g = R._g(P); L = P["L"]; x = g["hip"][0]; top = P["leg"] + 0.04 * L; bot = 0.012 * L
    z = bot + BAND_UP * (top - bot); f = (top - z) / (top - bot)
    return (x, g["hip"][1] - 0.01 * L * f, z)


def crane(seed=SEED):
    mats = [K.material(ASSET, 0, "pale sky-grey plumage", "C3C8CE", 0.85), K.material(ASSET, 1, "beak / legs (slate)", "3C3F44", 0.6),
            K.material(ASSET, 2, "blue-grey wing coverts", "8E99A6", 0.85), K.material(ASSET, 3, "black wingtips / eyes", "1E1E22", 0.7)]
    P = R.params(seed, ASSET, BODY)
    return R.recipe(ASSET, seed, materials=mats, spec=SPEC, body=BODY, clip_names=CLIPS, sockets=[("LegBand", "Leg_L", band_location(P))])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    m = crane(o.seed)
    with open(o.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    p = m["predicted"]; print(o.out, p["triangles"], p["lod1_triangles"], p["lod1_ratio"], p["dimensions"], p["bounds_min"], m["sockets"])
