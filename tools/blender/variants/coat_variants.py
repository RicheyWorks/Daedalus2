# SPDX-License-Identifier: MIT
"""Material-variant manifest for G28 Turing-coat pups (oddsreaper 48824, code 5ad9455a; mesh owner art-master-flex 48916).
Reusable: build(asset, slot, ...) works for any mesh whose one slot carries the coat.

What ships (no mesh change, no baked colour textures):
  <asset>.coat_variants.json   MI-ready params per variant, keyed to the TuringCoat coat keys (Coat.Pattern.coatKey):
                               CoatBase (vector), CoatPattern (vector), StormStreakMask (texture), StormStreakAmount (scalar 0..1)
  T_<asset>_StormStreakMask.png greyscale 8-bit mask, white = silver streak. Mob_CorsoPup has NO UVs, so the mask is a top-down
                               projection in UE mesh space (u = X across the back, v = Y along the body) sampled from Local Position.
Colours follow G28: EMBER and ASH blend to SMOKE (incomplete dominance), so SMOKE = 50/50 linear mix of EMBER and ASH, desaturated 60 %.
The coat key picks which G21 Gray-Scott field drives CoatBase -> CoatPattern (None = plain, the field stays at CoatBase);
the colour and storm-mark pick the MI. Dark/Accent slots are never touched.
Usage: python coat_variants.py --out <dir>"""
import argparse, hashlib, json, math, os, random, struct, zlib

SCHEMA = "bb-material-variants/1"
COAT_KEYS = ["Spots", "Stripes", "Labyrinth", "None"]          # = Coat.Pattern.coatKey() (5ad9455a), checked by the test
COLOURS = ["EMBER", "SMOKE", "ASH"]                             # = Coat.Colour
SRGB = {"EMBER": {"base": "9A4A2A", "pattern": "4A1C10"},       # warm burnt rust, charred pattern
        "ASH": {"base": "B8B3AB", "pattern": "6B6762"}}         # pale ash grey, darker grey pattern
SILVER = "D9DDE3"
DEFAULT_COAT = "3A3D44"                                          # the pup's current Coat slot colour (art-master-flex)


def s2l(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def l2s(c):
    c = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return max(0, min(255, int(round(c * 255))))


def lin(h):
    return [round(s2l(int(h[i:i + 2], 16)), 6) for i in (0, 2, 4)]


def hexof(l):
    return "".join("%02X" % l2s(c) for c in l)


def colours():
    out = {k: dict(v) for k, v in SRGB.items()}
    out["SMOKE"] = {k: hexof(smoke_mix(lin(SRGB["EMBER"][k]), lin(SRGB["ASH"][k]))) for k in ("base", "pattern")}
    return {k: out[k] for k in COLOURS}


SMOKE_DESAT = 0.6


def smoke_mix(e, a):
    """SMOKE = 50/50 linear blend of EMBER and ASH, then 60 % toward its own luminance so it reads as smoke, not rose."""
    m = [(x + y) / 2 for x, y in zip(e, a)]; Y = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]
    return [c + (Y - c) * SMOKE_DESAT for c in m]


def mi_name(asset, colour, storm):
    return "MI_%s_Coat_%s%s" % (asset, colour.capitalize(), "_Storm" if storm else "")


def streak_mask(w=256, h=512, seed=2028):
    """Jagged silver streak down the spine: v = 0.08..0.92, centre u wanders +-0.08 in seeded zig-zags, soft 1.5 px edge."""
    r = random.Random(seed); knots = [(0.08, 0.5)]
    v = 0.08
    while v < 0.92:
        v = min(0.92, v + r.uniform(0.07, 0.12)); knots.append((v, 0.5 + r.uniform(-0.08, 0.08)))
    rows = []
    for y in range(h):
        vv = (y + 0.5) / h; row = bytearray(w)
        if knots[0][0] <= vv <= knots[-1][0]:
            k = next(i for i in range(len(knots) - 1) if knots[i][0] <= vv <= knots[i + 1][0])
            (v0, u0), (v1, u1) = knots[k], knots[k + 1]; t = (vv - v0) / (v1 - v0) if v1 > v0 else 0
            uc = u0 + (u1 - u0) * t
            taper = min(1.0, (vv - 0.08) / 0.1, (0.92 - vv) / 0.1)
            half = (0.06 + 0.035 * taper) * w
            for x in range(w):
                d = abs((x + 0.5) - uc * w) - half
                row[x] = 255 if d <= -1.5 else (0 if d >= 1.5 else int(round(255 * (1.5 - d) / 3.0)))
        rows.append(bytes(row))
    return w, h, rows


def write_png_grey(path, w, h, rows):
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def build(asset="Mob_CorsoPup", slot="Coat", slot_index=0, bounds_cm=(-11.0, 11.0, -38.5, 31.5), untouched=("Dark", "Accent"),
          mask_file=None, mask_sha=None, mesh_sha=None):
    C = colours(); mask = mask_file or "T_%s_StormStreakMask.png" % asset
    variants = []
    for col in COLOURS:
        for storm in (False, True):
            variants.append({"name": mi_name(asset, col, storm), "colour": col, "storm_marked": storm, "params": {
                "CoatBase": {"type": "vector", "srgb_hex": C[col]["base"], "linear_rgba": lin(C[col]["base"]) + [1.0]},
                "CoatPattern": {"type": "vector", "srgb_hex": C[col]["pattern"], "linear_rgba": lin(C[col]["pattern"]) + [1.0]},
                "StormStreakMask": {"type": "texture", "file": mask},
                "StormStreakAmount": {"type": "scalar", "value": 1.0 if storm else 0.0}}})
    lookup = {"%s/%s%s" % (k, col, "/Storm" if st else ""): mi_name(asset, col, st) for k in COAT_KEYS for col in COLOURS for st in (False, True)}
    return {"schema": SCHEMA, "asset": asset, "mesh_sha256": mesh_sha, "mesh_owner": "art-master-flex (G21, PR212); mesh untouched",
            "slot": slot, "slot_index": slot_index, "untouched_slots": list(untouched), "default_coat_srgb_hex": DEFAULT_COAT,
            "gap": "G28 (oddsreaper 48824, code 5ad9455a com.daedalus.world.odds.breeding)",
            "parent_material": {"name": "M_TuringCoat (UE side, not built yet: UNREAL-QUEUE 6.G21)",
                                "graph": "Coat = lerp(CoatBase, CoatPattern, G21 field); final = lerp(Coat, StormStreakColour, StormStreakMask(uv) * StormStreakAmount)",
                                "storm_streak_colour": {"srgb_hex": SILVER, "linear_rgba": lin(SILVER) + [1.0], "metallic": 0.8, "roughness": 0.35},
                                "pattern_note": "coat key picks the G21 Gray-Scott field; None = plain (field 0, CoatBase only)"},
            "params": {"CoatBase": "vector, linear", "CoatPattern": "vector, linear", "StormStreakMask": "texture, greyscale, sRGB off", "StormStreakAmount": "scalar 0..1 (fade)"},
            "mask": {"file": mask, "sha256": mask_sha, "format": "PNG 8-bit greyscale, white = streak", "uv": "no mesh UVs: top-down projection in UE mesh space",
                     "u": {"axis": "X", "min_cm": bounds_cm[0], "size_cm": round(bounds_cm[1] - bounds_cm[0], 4)},
                     "v": {"axis": "Y", "min_cm": bounds_cm[2], "size_cm": round(bounds_cm[3] - bounds_cm[2], 4)},
                     "material_hint": "uv = ((LocalPosition.X - u.min) / u.size, (LocalPosition.Y - v.min) / v.size); clamp"},
            "coat_keys": COAT_KEYS, "colours": COLOURS, "variants": variants, "lookup": lookup,
            "status": "STAGED NOT READY (MI params only; the parent material is a UE editor step)"}


def write(out, asset="Mob_CorsoPup", mesh_sha=None):
    os.makedirs(out, exist_ok=True)
    w, h, rows = streak_mask(); mf = "T_%s_StormStreakMask.png" % asset
    ms = write_png_grey(os.path.join(out, mf), w, h, rows)
    m = build(asset, mask_file=mf, mask_sha=ms, mesh_sha=mesh_sha)
    p = os.path.join(out, asset + ".coat_variants.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    return p, m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--asset", default="Mob_CorsoPup"); ap.add_argument("--mesh-sha")
    o = ap.parse_args(); p, m = write(o.out, o.asset, o.mesh_sha)
    print(p, len(m["variants"]), "variants", len(m["lookup"]), "lookup keys", m["mask"]["sha256"][:12], {c: v["base"] for c, v in colours().items()})
