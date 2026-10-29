# SPDX-License-Identifier: MIT
"""Bird rig proportion pass (blender-team, 2026-10-29, buffffff 57464 next job). Raptor variants on creatures/bird_rig.py (blender-bird/v1)
using the new opt-in proportions presets (short tarsus, short neck) and the opt-in upright perch posture (hawk/kestrel 35 deg, owl 45 deg; owl: short owl beak + facial disc): defaults unchanged, gull / crane / juvenile pins byte-identical.
  Mob_Bird_Hawk     ~0.55 m buteo-style hawk, proportions "raptor", hooked beak, talons, fingered primaries, 3 tail bands
  Mob_Bird_Owl      ~0.5 m owl, proportions "owl" (almost no neck, big head), hooked beak, talons, 2 tail bands
  Mob_Bird_Kestrel  ~0.34 m small falcon, proportions "raptor" + small-bird head, pointed (plain) wingtips, 1 black tail band
All: clips Idle / Squawk / Walk / Fly; SOCKET_Talon (Leg_L, foot), SOCKET_Head (Head) - same as Mob_Marsh_Hawk (rebuilt in marsh_g504.py).
Usage: python bird_pass_20261029.py --out-dir data/contest   (writes bird_pass_<name>.quad.json)"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures")); sys.path.insert(0, HERE)
import kitlib as K
import bird_rig as R

SEED = 51029
ASK = "buffffff 57464 (bird rig proportion pass)"
CLIPS = ("Idle", "Squawk", "Walk", "Fly")
V = {"Mob_Bird_Hawk": ({"length": 0.55, "height_frac": 0.7, "proportions": "raptor", "posture": "perch", "perch_deg": 35.0, "neck_r": 0.95, "wing_lift_deg": 34.0, "tail_off": 0.16, "squawk_deg": 30.0,
                        "beak_style": "hook", "feet": "talons", "wing_tips": "fingered", "tail_bands": 3},
                       [("brown back plumage", "6E4A30"), ("hooked beak / talons (dark horn)", "2A2420"), ("pale barred underwing", "C8B496"), ("dark tips / eyes", "1E1A18")], "~0.55 m long"),
     "Mob_Bird_Owl": ({"length": 0.5, "height_frac": 0.66, "proportions": "owl", "posture": "perch", "perch_deg": 45.0, "facial_disc": True, "neck_r": 1.4, "wing_lift_deg": 30.0, "tail_off": 0.14, "squawk_deg": 22.0,
                       "beak_style": "owl", "feet": "talons", "wing_tips": "plain", "tail_bands": 2},
                      [("mottled tawny plumage", "8C6E4E"), ("beak / talons (pale horn)", "B8A68A"), ("buff facial disc / wings", "D2BE96"), ("dark eyes / bars", "201A14")], "~0.5 m long"),
     "Mob_Bird_Kestrel": ({"length": 0.34, "height_frac": 0.7, "proportions": "raptor", "posture": "perch", "perch_deg": 35.0, "head_scale": 1.15, "neck_r": 0.9, "wing_lift_deg": 36.0, "tail_off": 0.2,
                           "squawk_deg": 34.0, "beak_style": "hook", "feet": "talons", "wing_tips": "plain", "tail_bands": 1},
                          [("rufous spotted back", "B8643A"), ("beak / talons (slate)", "3A3A44"), ("blue-grey wings / head", "7C8696"), ("black tail band / eyes", "141418")], "~0.34 m long")}


def bird(a, seed):
    body, mats, size = V[a]
    M = [K.material(a, i, n, h, 0.85 if i != 1 else 0.5) for i, (n, h) in enumerate(mats)]
    P = R.params(seed, a, body); g = R._g(P)
    socks = [("Talon", "Leg_L", (g["hip"][0], g["hip"][1] - 0.02 * P["L"], 0.02 * P["L"])), ("Head", "Head", (0, g["head"][0], g["head"][1]))]
    spec = {"asker": ASK, "size_m": size, "tri_cap": 6000, "lod": "LOD0/1", "collision": "capsule in UE", "proportions": body["proportions"],
            "rig": "blender-bird/v1 (bird_rig.py), rigid; clips " + ", ".join(CLIPS), "sockets": "SOCKET_Talon (Leg_L), SOCKET_Head (Head)", "status": "NOT READY"}
    return R.recipe(a, seed, materials=M, spec=spec, body=body, clip_names=CLIPS, sockets=socks)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", required=True); o = ap.parse_args()
    for i, a in enumerate(V):
        m = bird(a, SEED + i); fn = "bird_pass_%s.quad.json" % a.replace("Mob_Bird_", "").lower()
        with open(os.path.join(o.out_dir, fn), "w", encoding="utf-8", newline="\n") as f: json.dump(m, f, indent=1); f.write("\n")
        print(fn, m["predicted"]["triangles"], m["predicted"]["dimensions"], [s["name"] for s in m["sockets"]])
