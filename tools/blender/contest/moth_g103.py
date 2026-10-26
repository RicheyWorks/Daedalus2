# SPDX-License-Identifier: MIT
"""G103 Soot Moths: Mob_Moth_Peppered (pythagoras 49770, pyth-g103-assets-20261019; code 9fcb07bd battlefield.SootMoths,
docs MOTH01: "moth pair (dark and pale, ~4 cm, resting pose)"). Built on the reusable creatures/insect_rig.py (blender-insect/v1),
built by creatures/build_quadruped.py; pinned at data/contest/g103_moth.quad.json.
Morphs: ONE mesh, slot 0 "Morph" (wings + body) takes MI_Mob_Moth_Peppered_Pale or _Dark (one master M_MothPeppered),
slot 1 eyes/legs/antennae stays dark. SootMoths has two morphs (dark D dominant, share 1 - (1 - q)^2), so UE spawns each moth
with the MI for its morph. Pale (typica): cream with black pepper speckles + cross-lines from T_Mob_Moth_Peppered_PepperMask
(top-down local projection, G28 style: kit meshes carry no UVs). Dark (carbonaria): near-black, pepper faint.
REUSE check: catalog Mob_Moth_Luna / Mob_Lumamoth / Mob_Butterfly are static (0 skins, 0 clips), so a new rig.
Usage: python moth_g103.py --out data/contest/g103_moth.quad.json [--morphs <dir>]"""
import argparse, hashlib, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("kit", "creatures", "decals"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import kitlib as K
import insect_rig as I
import decalkit as DK

SEED = 1031
MOTH = "Mob_Moth_Peppered"
SPEC = {"gap": "G103", "size_m": "4.5 cm wingspan at rest", "tri_cap": 1500, "lod": "LOD0/1", "rig": "insect_rig: 10 bones, rigid; Idle (rest on bark), Flutter",
        "asker": "pythagoras 49770", "morphs": "slot 0 Morph -> MI _Pale / _Dark"}
MORPHS = {"Pale": {"MorphBase": "E4DED0", "Pepper": "24211E", "PepperAmount": 1.0, "Roughness": 0.85, "genotype": "dd (typica)", "SootMoths": "pale share = (1 - q)^2"},
          "Dark": {"MorphBase": "2B2825", "Pepper": "161412", "PepperAmount": 0.3, "Roughness": 0.8, "genotype": "DD or Dd (carbonaria, D dominant)", "SootMoths": "dark share = 1 - (1 - q)^2"}}


def moth(seed=SEED):
    mats = [K.material(MOTH, 0, "Morph (wings + body; MI _Pale / _Dark)", MORPHS["Pale"]["MorphBase"], 0.85), K.material(MOTH, 1, "eyes / legs / antennae", "2A2622", 0.7)]
    return I.recipe(MOTH, seed, materials=mats, spec=SPEC)


def lin(hexv):
    c = [int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 6) for v in c] + [1.0]


def pepper_mask(m, seed=SEED, w=512):
    """White = black pepper. Grid in UE local cm (UE = 100 * (x, -y, z)); u along UE X, v along UE Y."""
    lo, hi = m["predicted"]["bounds_min"], m["predicted"]["bounds_max"]
    umin, usize = round(lo[0] * 100, 3), round((hi[0] - lo[0]) * 100, 3); vmin, vsize = round(-hi[1] * 100, 3), round((hi[1] - lo[1]) * 100, 3)
    h = int(round(w * vsize / usize)); rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:h, 0:w]; X = (umin + (u + 0.5) / w * usize) / 100; Yb = -(vmin + (v + 0.5) / h * vsize) / 100
    fine = DK.vnoise(rng, h, w, h // 3, w // 3, 1); spk = np.clip((fine - 0.62) / 0.08, 0, 1)                    # dense pepper dots
    sx = np.abs(X) / (usize / 200)                                                                             # 0 at the body, 1 at the apex
    lines = np.zeros_like(X)
    for k, (y0, amp) in enumerate(((-0.004, 0.0012), (0.002, 0.0016), (0.0075, 0.0014))):                     # wavy cross-lines across the wings
        yl = y0 + 0.006 * sx + amp * np.sin(sx * 9 + k)
        lines = np.maximum(lines, np.clip(1 - np.abs(Yb - yl) / 0.00045, 0, 1) * (sx > 0.12))
    mask = np.clip(np.maximum(spk * 0.9, lines), 0, 1)
    return mask, {"u": {"axis": "X", "min_cm": umin, "size_cm": usize}, "v": {"axis": "Y", "min_cm": vmin, "size_cm": vsize}}


def morph_manifest(m, out, seed=SEED):
    from PIL import Image
    os.makedirs(out, exist_ok=True); mask, uv = pepper_mask(m, seed); fn = "T_%s_PepperMask.png" % MOTH
    Image.fromarray(np.round(mask * 255).astype(np.uint8), "L").save(os.path.join(out, fn), optimize=True)
    sha = hashlib.sha256(open(os.path.join(out, fn), "rb").read()).hexdigest()
    mi = {}
    for k, v in MORPHS.items():
        mi["MI_%s_%s" % (MOTH, k)] = {"parent": "M_MothPeppered", "morph": k, "genotype": v["genotype"], "share_in_code": v["SootMoths"],
                                       "params": {"MorphBase": {"srgb_hex": v["MorphBase"], "linear_rgba": lin(v["MorphBase"])}, "Pepper": {"srgb_hex": v["Pepper"], "linear_rgba": lin(v["Pepper"])},
                                                  "PepperAmount": v["PepperAmount"], "Roughness": v["Roughness"], "PepperMask": fn}}
    man = {"schema": "bb-material-variants/1", "asset": MOTH, "slot": "Morph", "slot_index": 0, "untouched_slots": ["eyes / legs / antennae"],
           "gap": "G103 (pythagoras 49770, code 9fcb07bd com.daedalus.world.battlefield.SootMoths)", "status": "NOT READY",
           "parent_material": {"name": "M_MothPeppered (UE side)", "graph": "BaseColor = lerp(MorphBase, Pepper, PepperMask(uv) * PepperAmount); Roughness = Roughness"},
           "params": {"MorphBase": "vector, linear", "Pepper": "vector, linear", "PepperAmount": "scalar 0..1", "Roughness": "scalar", "PepperMask": "texture, greyscale, sRGB off"},
           "mask": {"file": fn, "sha256": sha, "format": "PNG 8-bit greyscale, white = pepper", "uv": "no mesh UVs: top-down projection in UE mesh space", **uv,
                    "material_hint": "uv = ((LocalPosition.X - u.min) / u.size, (LocalPosition.Y - v.min) / v.size); clamp. Wings flap in Flutter: use the reference (bind) pose "
                                     "position (PreSkinnedLocalPosition) so the pattern sticks to the wing."},
           "instances": mi, "spawn": "per moth: morph = Dark with probability SootMoths dark share (1 - (1 - q)^2), else Pale"}
    with open(os.path.join(out, MOTH + ".morph_variants.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1); f.write("\n")
    return man, mask


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--morphs"); o = ap.parse_args()
    m = moth(o.seed)
    with open(o.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    p = m["predicted"]; print(o.out, p["triangles"], p["lod1_triangles"], p["lod1_ratio"], p["dimensions"], p["bounds_min"])
    if o.morphs:
        man = morph_manifest(m, o.morphs, o.seed)[0]; print("morphs", list(man["instances"]), man["mask"]["sha256"][:12])
