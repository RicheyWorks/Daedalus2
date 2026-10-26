# SPDX-License-Identifier: MIT
"""G33 Seed-Song Spring water kit (youtube-master 48984, ytm-g33-assets-20261019; code main 325f5655 brew.story.SpringChain).
Same approach as G28 (coat_variants.py): no mesh is re-exported. The 12 island springs REUSE shipped meshes, and only their
water slot gets an MI, picked by SpringChain.clean(id): false -> Cloudy (gives raw_water), true -> Clear (gives water).
  spring_1  Homestead Well  -> Prop_Well (shipped, /Game/Daedalus/Art/Prop/Prop_Well), water slot Prop_Well_M2
  spring_2..12              -> Prop_Water_AMF_SpringBasin_V1..V8 (art-master-flex), water slot M_AMF_water; V1..V3 repeat
                               for springs 10-12 with a yaw offset so neighbours don't match.
What ships:
  G33_SpringWater.spring_variants.json  2 MIs (MI_Spring_Water_Cloudy / _Clear) with WaterShallow, WaterDeep (vector),
      Turbidity, Opacity, Roughness, SongClear (scalar 0..1 fade for the clearing moment), SiltMask (texture), SiltTiling;
      plus a lookup per spring id: mesh, water slot, yield, MI per state.
  T_Spring_SiltMask.png  256x256 8-bit greyscale, tileable seeded value noise (white = silt), world-aligned XY in UE.
Usage: python spring_water.py --out <dir> [--mesh-sha Asset=sha ...]"""
import argparse, json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coat_variants import lin, write_png_grey

SCHEMA = "bb-material-variants/1"
SPRINGS = ["Homestead Well", "Reed Seep", "Ferry Steps", "Goat Ledge", "Old Ark Keel", "Bell Hollow", "Mist Stair", "Lantern Pool",
           "Broken Choir", "Cloudfoot", "Needle Falls", "Summit Basin"]          # = SpringChain.island() (325f5655), checked by the test
STATES = ["Cloudy", "Clear"]
WATER = {"Cloudy": {"WaterShallow": "8A8468", "WaterDeep": "4E4A3A", "Turbidity": 0.85, "Opacity": 0.95, "Roughness": 0.55, "SongClear": 0.0},
         "Clear": {"WaterShallow": "7FD3E6", "WaterDeep": "1E6E8C", "Turbidity": 0.05, "Opacity": 0.55, "Roughness": 0.08, "SongClear": 1.0}}
WELL = {"mesh": "Prop_Well", "slot": "Prop_Well_M2", "slot_index": 2, "path": "art/glb/Prop_Well.glb",
        "owner": "shipped catalog prop (art QUEUE 273, in Unreal at /Game/Daedalus/Art/Prop/Prop_Well)"}
BASIN = {"slot": "M_AMF_water", "slot_index": 1, "owner": "art-master-flex"}
MASK = "T_Spring_SiltMask.png"


def mi(state):
    return "MI_Spring_Water_" + state


def spring_mesh(i):
    """i = 0-based spring index -> (mesh, slot, slot_index, yaw_deg, path, owner)."""
    if i == 0:
        return WELL["mesh"], WELL["slot"], WELL["slot_index"], 0, WELL["path"], WELL["owner"]
    v = (i - 1) % 8 + 1; yaw = 0 if i <= 8 else 137 * ((i - 1) // 8)
    return "Prop_Water_AMF_SpringBasin_V%d" % v, BASIN["slot"], BASIN["slot_index"], yaw, "art/glb/amf/Prop_Water_AMF_SpringBasin_V%d.glb" % v, BASIN["owner"]


def silt_mask(n=256, seed=3333, cells=(8, 16, 32), weights=(0.55, 0.3, 0.15)):
    """Tileable value noise: per octave a periodic lattice (wraps at the edge), smoothstep-bilinear, summed, then contrast."""
    r = random.Random(seed); octs = [[[r.random() for _ in range(c)] for _ in range(c)] for c in cells]
    def sm(t):
        return t * t * (3 - 2 * t)
    rows = []
    for y in range(n):
        row = bytearray(n)
        for x in range(n):
            v = 0.0
            for g, c, w in zip(octs, cells, weights):
                fx, fy = x * c / n, y * c / n; ix, iy = int(fx), int(fy); tx, ty = sm(fx - ix), sm(fy - iy)
                a, b = g[iy % c][ix % c], g[iy % c][(ix + 1) % c]; d, e = g[(iy + 1) % c][ix % c], g[(iy + 1) % c][(ix + 1) % c]
                v += w * ((a + (b - a) * tx) * (1 - ty) + (d + (e - d) * tx) * ty)
            row[x] = max(0, min(255, int(round(255 * min(1.0, max(0.0, (v - 0.35) / 0.4))))))
        rows.append(bytes(row))
    return n, n, rows


def build(mask_sha=None, mesh_sha=None):
    mesh_sha = mesh_sha or {}
    variants = []
    for st in STATES:
        W = WATER[st]; P = {}
        for k in ("WaterShallow", "WaterDeep"):
            P[k] = {"type": "vector", "srgb_hex": W[k], "linear_rgba": lin(W[k]) + [1.0]}
        for k in ("Turbidity", "Opacity", "Roughness", "SongClear"):
            P[k] = {"type": "scalar", "value": W[k]}
        P["SiltMask"] = {"type": "texture", "file": MASK}; P["SiltTiling"] = {"type": "scalar", "value": 0.5}
        variants.append({"name": mi(st), "state": st, "spring_chain_clean": st == "Clear", "draw_item": "water" if st == "Clear" else "raw_water", "params": P})
    springs = {}
    for i, nm in enumerate(SPRINGS):
        mesh, slot, si, yaw, path, owner = spring_mesh(i)
        springs["spring_%d" % (i + 1)] = {"name": nm, "yield": 4 + i // 3, "mesh": mesh, "mesh_path": path, "mesh_sha256": mesh_sha.get(mesh), "mesh_owner": owner,
                                          "water_slot": slot, "water_slot_index": si, "yaw_offset_deg": yaw,
                                          "mi": {st: mi(st) for st in STATES}, "first": i == 0}
    lookup = {"%s/%s" % (sid, st): mi(st) for sid in springs for st in STATES}
    return {"schema": SCHEMA, "kit": "G33_SpringWater", "gap": "G33 (youtube-master 48984, code 325f5655 com.daedalus.world.brew.story)",
            "rule": "state = SpringChain.clean(springId) ? Clear : Cloudy; on purifyNext() fade SongClear 0 -> 1 (about 2 s) then swap to MI_Spring_Water_Clear",
            "meshes": "REUSED, untouched: no glb re-export; only the water slot gets the MI",
            "parent_material": {"name": "M_SpringWater (UE side, not built yet: UNREAL-QUEUE G33)", "blend": "translucent or masked water surface",
                                "graph": "silt = SiltMask(worldXY * SiltTiling) * Turbidity; colour = lerp(WaterShallow, WaterDeep, depth or 0.5) then lerp toward WaterShallow by silt; "
                                         "opacity = Opacity; roughness = lerp(Roughness, 0.6, silt); SongClear lerps every param from the Cloudy MI values to the Clear ones"},
            "params": {"WaterShallow": "vector, linear", "WaterDeep": "vector, linear", "Turbidity": "scalar 0..1", "Opacity": "scalar 0..1",
                       "Roughness": "scalar 0..1", "SongClear": "scalar 0..1 (fade)", "SiltMask": "texture, greyscale, sRGB off, tiling", "SiltTiling": "scalar, per metre"},
            "mask": {"file": MASK, "sha256": mask_sha, "format": "PNG 8-bit greyscale 256x256, tileable, white = silt", "uv": "world-aligned XY (no mesh UVs needed)"},
            "states": STATES, "variants": variants, "springs": springs, "lookup": lookup, "spring_order": list(springs),
            "status": "STAGED NOT READY (MI params only; the parent material and spring actors are UE editor steps)"}


def write(out, mesh_sha=None):
    os.makedirs(out, exist_ok=True)
    w, h, rows = silt_mask(); ms = write_png_grey(os.path.join(out, MASK), w, h, rows)
    m = build(ms, mesh_sha)
    p = os.path.join(out, "G33_SpringWater.spring_variants.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    return p, m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--mesh-sha", nargs="*", default=[])
    o = ap.parse_args(); p, m = write(o.out, dict(kv.split("=", 1) for kv in o.mesh_sha))
    print(p, len(m["variants"]), "MIs", len(m["springs"]), "springs", len(m["lookup"]), "lookup keys", m["mask"]["sha256"][:12])
