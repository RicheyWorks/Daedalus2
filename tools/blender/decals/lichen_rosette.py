# SPDX-License-Identifier: MIT
"""Map-lichen (Rhizocarpon geographicum) rosette decals on rock, S / M / L, built on decalkit.py (reusable).
First use: Decal_Rock_Lichen, G91 Lichen Clock (pythagoras 49650, pyth-g91-assets-20261019; code 1d8ebbe9
daedalus-core/.../battlefield/LichenClock.java). Sizes are keyed to the code's growth curve, LichenClock.Settings.DEFAULT:
lag 8 yr, great growth phase 0.6 mm/yr for 50 yr, then 0.3 mm/yr; falls 30-220 yr ago (largest possible thallus 78.6 mm).
  S  15 mm thallus = 25 yr of growth (young colonist / recent fall, ~33 yr at zero delay)
  M  30 mm         = 50 yr, end of the great growth phase (~58 yr)
  L  60 mm         = 150 yr (~158 yr); scale L's DecalSize up to 1.31x for the 78.6 mm maximum
Look: chartreuse areoles (a jittered Voronoi, ~0.9 mm cells, so bigger thalli carry more of them) split by black prothallus
cracks, a black prothallus rim, a lobed outline, older centres a little darker. Constant texel density (6.4 px/mm).
Outputs <out>/Decal_Rock_Lichen_<S|M|L>/ (T_*_BC/N/M.png + .decal.json) and <out>/Decal_Rock_Lichen.decals.json (size index).
Usage: python lichen_rosette.py --out <dir> [--seed 9191]"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decalkit as DK

ASSET = "Decal_Rock_Lichen"
CLOCK = {"lag": 8.0, "fastRate": 0.6, "fastYears": 50.0, "slowRate": 0.3, "minAge": 30, "maxAge": 220,
         "source": "LichenClock.Settings.DEFAULT (Daedalus2 1d8ebbe9)"}
SIZES = {"S": 25.0, "M": 50.0, "L": 150.0}               # years of growth -> diameter via curve()
FILL = 0.75                                               # thallus diameter / decal width
PX_PER_MM = 6.4
AREOLE_MM, CRACK_MM, RIM_MM, RELIEF_MM = 0.9, 0.22, 0.55, 0.35
AREOLE, AREOLE2, PROTHALLUS = np.array([200, 212, 58]), np.array([150, 176, 52]), np.array([28, 26, 23])


def curve(years, c=CLOCK):
    """LichenClock.curve: diameter in mm after `years` of growth."""
    if years <= 0:
        return 0.0
    if years <= c["fastYears"]:
        return c["fastRate"] * years
    return c["fastRate"] * c["fastYears"] + c["slowRate"] * (years - c["fastYears"])


def age(d_mm, c=CLOCK):
    """LichenClock.age: years since the fall for a thallus of d_mm (no colonisation delay)."""
    if not d_mm > 0:
        return c["lag"]
    fast = c["fastRate"] * c["fastYears"]
    return c["lag"] + (d_mm / c["fastRate"] if d_mm <= fast else c["fastYears"] + (d_mm - fast) / c["slowRate"])


def fields(seed, d_mm, w):
    """(mask, height in cm, colour) for one rosette of diameter d_mm on a w x w texture."""
    rng = np.random.default_rng(seed); h = w; decal_mm = w / PX_PER_MM; R = d_mm / 2
    v, u = np.mgrid[0:h, 0:w]; x = (u + 0.5) / w * 2 - 1; y = 1 - (v + 0.5) / h * 2
    xm, ym = x * decal_mm / 2, y * decal_mm / 2; th = np.arctan2(ym, xm)
    lobes = 1 + 0.035 * np.sin(5 * th + rng.uniform(0, 6.3)) + 0.025 * np.sin(11 * th + rng.uniform(0, 6.3)) + 0.16 * (DK.vnoise(rng, h, w, 7, 7, 3) - 0.5)
    rad = np.hypot(xm, ym) / (R * lobes)                                   # 1.0 = outer edge of the areolate body
    rim_out = 1 + RIM_MM / R
    mask = np.clip((rim_out - rad) * R * PX_PER_MM, 0, 1) * DK.border_window(x, y, w, h, 4)
    f1, f2, cid = DK.voronoi(rng, h, w, AREOLE_MM * PX_PER_MM)
    gap = (f2 - f1) / PX_PER_MM                                            # mm to the nearest areole boundary (x2)
    crack = np.clip((CRACK_MM - gap) / 0.08 + 0.5, 0, 1)                                  # black prothallus lines between areoles
    body = np.clip((1 - rad) * R * PX_PER_MM / 1.5, 0, 1)                  # areolate body (inside the rim)
    cell = (np.sin(cid * 12.9898) * 43758.5453) % 1                        # per-areole tint
    centre_age = np.clip(1 - rad, 0, 1) ** 1.5
    col = AREOLE * (1 - cell[..., None] * 0.45) + AREOLE2 * cell[..., None] * 0.45
    col = col * (1 - 0.3 * centre_age[..., None]) + np.array([96, 104, 40]) * 0.3 * centre_age[..., None]
    col = col * (1 - crack[..., None]) + PROTHALLUS * crack[..., None]
    col = col * body[..., None] + PROTHALLUS * (1 - body[..., None]) * (0.9 + 0.2 * DK.vnoise(rng, h, w, 9, 9, 2))[..., None]
    dome = np.sqrt(np.clip(gap / AREOLE_MM, 0, 1))                         # areoles domed, cracks low
    dome = dome * (1 - crack)
    hgt_mm = RELIEF_MM * (0.25 + 0.75 * dome * (1 - crack)) * body + 0.06 * (1 - body) * (rad < rim_out)
    return mask, hgt_mm / 10.0, np.clip(col, 0, 255)


def build(out, seed=9191, sizes=SIZES):
    index = {"schema": DK.SCHEMA + "/set", "asset": ASSET, "seed": seed, "generator": "tools/blender/decals/lichen_rosette.py", "status": "NOT READY",
             "clock": CLOCK, "max_diameter_mm": round(curve(CLOCK["maxAge"] - CLOCK["lag"]), 2), "sizes": {},
             "scale_rule": "for a thallus of d mm use the nearest size and scale DecalSize Y/Z by d / diameter_mm (0.8-1.31x keeps texel density sane)",
             "placement": "rock faces of the reused rock-kit boulders, X = surface normal, random roll 0-360; cluster 3-12 rosettes per boulder, the largest at the oldest (sun-facing) face"}
    mans = {}
    for k, yrs in sizes.items():
        d_mm = round(curve(yrs), 3); decal_mm = d_mm / FILL; w = int(round(decal_mm * PX_PER_MM)); a = "%s_%s" % (ASSET, k)
        mask, hgt, col = fields(seed + {"S": 0, "M": 1, "L": 2}.get(k, 0), d_mm, w)
        n = DK.normals(hgt, 1.0, decal_mm / 10, decal_mm / 10)
        dd = os.path.join(out, a); files, sha = DK.write_textures(dd, a, col, n, mask)
        man = DK.manifest(a, seed, index["generator"], files, sha, w, w, (decal_mm / 10, decal_mm / 10), 2.0, "M_Decal_RockLichen (Deferred Decal master)", 0.85,
                          index["placement"], axes="project along local -X into the rock; texture U = +Y, V = -Z (any roll)", relief_cm=RELIEF_MM / 10,
                          extra_params={"Desaturate": 0.0}, wiring="BaseColor = desaturate(BaseColorTex.rgb * BaseColorTint, Desaturate); Normal = FlattenNormal(NormalTex, 1-NormalStrength); "
                                                                   "Roughness = Roughness; Opacity = saturate(pow(OpacityTex.r, OpacityPower) * OpacityContrast)",
                          meta={"lichen": {"size": k, "diameter_mm": d_mm, "growth_years": yrs, "fall_age_years_zero_delay": round(age(d_mm), 2),
                                           "px_per_mm": PX_PER_MM, "fill": FILL}})
        DK.write_manifest(dd, man); mans[k] = man
        index["sizes"][k] = {"asset": a, "diameter_mm": d_mm, "growth_years": yrs, "fall_age_years_zero_delay": round(age(d_mm), 2),
                             "decal_cm": round(decal_mm / 10, 4), "texture_px": w, "manifest": "%s/%s.decal.json" % (a, a)}
    with open(os.path.join(out, ASSET + ".decals.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=1); f.write("\n")
    return index, mans


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=9191); o = ap.parse_args()
    idx = build(o.out, o.seed)[0]
    for k, s in idx["sizes"].items():
        print(k, s)
