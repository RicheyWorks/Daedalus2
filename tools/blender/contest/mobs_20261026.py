# SPDX-License-Identifier: MIT
"""Contest backlog creatures + Hornback sick MI, resumed 2026-10-26 (blender-team). Closes the partial DONEs of G156/G172/G176/G183.
  Mob_Thistle_Hare      G156 pythagoras 50322: ~45 cm island hare on quadruped_rig (15 bones, ornament "ears"); clips Idle, Hop
                        (the rig's Run gait, renamed), Freeze (held bind pose, 1 s loop); bone socket SOCKET_EarTag on Head (Prop_Ear_Tag).
  Mob_Silverfin_Shoal   G176 pythagoras 50545: one ~20 cm silver fish, rigid 4-bone swim rig (Root > Body > Tail > Fin), Swim loop;
                        UE instances it as a school (HISM / Niagara mesh), Density scalar 0..1 = fish per m^3 / 12 (spec.shoal).
  Mob_Ember_Fritillary  G183 pythagoras 50603: ~5 cm orange butterfly on insect_rig (wing "butterfly", antenna "clubbed"); Idle (on a
                        flower) + Flutter; instanced over a patch.
  MI_Mob_Lab_Hornback_Sick  G172 pythagoras 50449: G28-style MI params + greyscale masks (sick coat patches, hoof lesions) for the
                        staged Mob_Lab_Hornback slot 0 (hide) and slot 2 (hoof); side projection in UE mesh space, no UVs needed.
Usage: python mobs_20261026.py --out-dir data/contest [--masks <dir>]   -> <dir>/mob_<asset>.quad.json"""
import argparse, copy, hashlib, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("kit", "creatures"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import kitlib as K
import quadruped_rig as Q
import insect_rig as I
import bird_rig as R

SEED = 26102027
HARE, SHOAL, FRIT, HORN = "Mob_Thistle_Hare", "Mob_Silverfin_Shoal", "Mob_Ember_Fritillary", "Mob_Lab_Hornback"


def hare(seed=SEED):
    # polish 2026-10-26b: long ears, paw feet, a 2-link fluffy tail; rounded body + haunches added below as extra parts
    body = {"body_h": 0.36, "body_w": 0.3, "leg": 0.3, "plates": 0, "tail": 0.05, "head_lift": 0.08, "ornament": "ears", "ear": 0.42,
            "tail_bones": 2, "tail_bush": 0.16, "tail_curl": 70.0, "feet": "paw"}
    mats = [K.material(HARE, 0, "thistle-grey hare fur", "9C8C78", 0.95), K.material(HARE, 1, "ear tips / eyes", "3A3028", 0.8), K.material(HARE, 2, "paws / tail puff (cream)", "E8E0D0", 0.95)]
    spec = {"gap": "G156", "asker": "pythagoras 50322", "size_m": "~45 cm", "tri_cap": 3000, "lod": "LOD0/1",
            "rig": "quadruped_rig 15 bones; clips Idle, Hop (Run gait), Freeze", "sockets": "SOCKET_EarTag on Head (Prop_Ear_Tag)"}
    m = Q.recipe(HARE, seed, 0.52, materials=mats, spec=spec, body=body, clip_names=("Idle", "Run"))
    c = m["clips"]; c["Hop"] = c.pop("Run")
    fr = copy.deepcopy(c["Idle"]); fr["frames"], fr["seconds"], fr["loop"] = 30, 1.0, True
    fr["tracks"] = {b: {ch: [[0, keys[0][1]], [30, keys[0][1]]] for ch, keys in t.items()} for b, t in fr["tracks"].items()}
    c["Freeze"] = fr
    bb = {b["name"]: b for b in m["bones"]}
    def mid(b, f=0.5): return [bb[b]["head"][i] + f * (bb[b]["tail"][i] - bb[b]["head"][i]) for i in range(3)]
    def ball(name, c, rx, ry, rz, slot, bone, seg=10):
        prof = [(round(math.sin(math.pi * k / 6) * 1.0, 4), round(-math.cos(math.pi * k / 6), 4)) for k in range(7)]
        q = K.lathe(name, [(r * rx, z * rz) for r, z in prof], (c[0], c[1], c[2]), slot, segments=seg, lod1={"segments": 6})
        q["scale_y"] = round(ry / rx, 4); q["bone"] = bone; return q
    sc = mid("Spine"); hp = bb["Hips"]["head"]; tl = [b["name"] for b in m["bones"] if b["name"].startswith("Tail")][-1]
    extra = [ball("BodyRound", sc, 0.105, 0.105, 0.1, 0, "Spine"), ball("ChestRound", mid("Chest"), 0.09, 0.09, 0.09, 0, "Chest")]
    for s, nm in ((1, "L"), (-1, "R")):
        extra.append(ball("Haunch" + nm, (hp[0] + s * 0.07, hp[1] + 0.02, hp[2] - 0.03), 0.075, 0.075, 0.085, 0, "Hips"))
    extra.append(ball("TailPuff", bb[tl]["tail"], 0.045, 0.045, 0.045, 2, tl, 8))
    for q in extra: q.pop("scale_y", None)
    m["parts"] += extra
    Qp = m["parts"]; lo, hi = K.bounds(Qp)
    t0 = sum(K.part_tris(x) for x in Qp if K.in_lod(x, 0)); t1 = sum(K.part_tris(x, 1) for x in Qp if K.in_lod(x, 1))
    m["predicted"].update({"triangles": t0, "lod1_triangles": t1, "lod1_ratio": round(t1 / t0, 3), "bounds_min": lo, "bounds_max": hi, "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)]})
    m["spec"]["polish"] = "2026-10-26b: ears 0.42 x length, rounded body/chest + haunch lathes, 2-link fluffy tail with a cream TailPuff (slot 2)"
    head = bb["Head"]
    tip = [round(head["head"][i] + 0.6 * (head["tail"][i] - head["head"][i]), 4) for i in range(3)]
    tip[0] += 0.03; tip[2] += 0.05
    m["sockets"] = R.bone_sockets(m["bones"], [("EarTag", "Head", tuple(tip))])
    m["unreal"]["type"] = "skeletal mesh + 3 anim sequences (Idle, Hop, Freeze), root bone 'Root'"; m["unreal"]["sockets"] = "SOCKET_EarTag (Head)"
    return m


def shoal(seed=SEED):
    L = 0.2; z = 0.0
    B = [{"name": "Root", "parent": None, "head": [0, 0, 0], "tail": [0, 0.02, 0]},
         {"name": "Body", "parent": "Root", "head": [0, -0.1, z], "tail": [0, 0.02, z]},
         {"name": "Tail", "parent": "Body", "head": [0, 0.02, z], "tail": [0, 0.08, z]},
         {"name": "Fin", "parent": "Tail", "head": [0, 0.08, z], "tail": [0, 0.1, z]}]
    P = [dict(K.lathe("Body", [(0.0, -0.1), (0.018, -0.07), (0.024, -0.02), (0.016, 0.03), (0.0, 0.05)], (0, 0, z), 0, segments=8, rot=(-90, 0, 0)), bone="Body", rigid=True)]
    P.append(dict(K.cyl("Peduncle", "y", 0.012, 0.005, 0.05, (0, 0.055, z), 0, 6), bone="Tail", rigid=True))
    P.append(dict(K.slab("TailFin", [(0, 0.0), (0.03, 0.025), (0.0, 0.012), (-0.03, 0.025)], 0.002, (0, 0.08, z), 1, rot=(90, 0, 90)), bone="Fin", rigid=True))
    P.append(dict(K.slab("Dorsal", [(-0.02, 0.0), (0.02, 0.0), (0.0, 0.018)], 0.002, (0, -0.02, z + 0.022), 1, rot=(90, 0, 90)), bone="Body", rigid=True))
    P.append(dict(K.box("EyeL", (0.004, 0.006, 0.006), (0.014, -0.075, z + 0.006), 2, bevel=False), bone="Body", rigid=True))
    P.append(dict(K.box("EyeR", (0.004, 0.006, 0.006), (-0.014, -0.075, z + 0.006), 2, bevel=False), bone="Body", rigid=True))
    n = 24
    def wave(amp, ph):
        return [[f, [0.0, 0.0, round(amp * math.sin(2 * math.pi * f / n + ph), 5)]] for f in range(0, n + 1, 2)]
    C = {"Swim": {"frames": n, "fps": 30, "loop": True, "seconds": n / 30, "tracks": {"Body": {"rot": wave(0.08, 0)}, "Tail": {"rot": wave(0.35, -1.0)}, "Fin": {"rot": wave(0.45, -2.0)}}}}
    mats = [K.material(SHOAL, 0, "silver scales", "C8D0D8", 0.35, 0.6), K.material(SHOAL, 1, "fins", "8898A8", 0.5), K.material(SHOAL, 2, "eyes", "101418", 0.3)]
    lo, hi = K.bounds(P); lo1, hi1 = K.bounds(P, 1)
    t0 = sum(K.part_tris(p) for p in P if K.in_lod(p, 0)); t1 = sum(K.part_tris(p, 1) for p in P if K.in_lod(p, 1))
    return {"asset": SHOAL, "kind": "Mob", "schema": "blender-fish/v1", "seed": seed, "params": {"length": L}, "materials": mats, "bones": B, "parts": P, "clips": C,
            "bind_mode": "rigid", "bind": "rigid per part (bind_mode rigid): every part 100% on its bone",
            "spec": {"gap": "G176", "asker": "pythagoras 50545", "size_m": "~20 cm fish", "tri_cap": 400, "lod": "LOD0/1", "rig": "4 rigid bones; Swim loop",
                     "shoal": {"instance": "HISM or Niagara mesh renderer, one mesh per fish", "Density": "scalar 0..1 -> 0..12 fish per m^3", "phase": "randomise Swim start time per fish"}},
            "axes": K.AXES, "status": "STAGED NOT READY",
            "unreal": {"type": "skeletal mesh + 1 anim sequence (Swim), root bone 'Root'", "nanite": "n/a", "collision": "none (instanced)", "sockets": "none"},
            "predicted": {"triangles": t0, "lod1_triangles": t1, "lod1_ratio": round(t1 / t0, 3), "bounds_min": lo, "bounds_max": hi,
                          "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)], "bones": len(B)}}


def fritillary(seed=SEED):
    mats = [K.material(FRIT, 0, "ember orange wings (black chequer = MI mask later)", "E8761E", 0.8), K.material(FRIT, 1, "body / legs / antennae", "2A2018", 0.7)]
    spec = {"gap": "G183", "asker": "pythagoras 50603", "size_m": "~5 cm wingspan", "tri_cap": 1500, "lod": "LOD0/1", "rig": "insect_rig 10 bones rigid; Idle (on flower), Flutter",
            "instancing": "instanced over a patch; randomise clip start"}
    return I.recipe(FRIT, seed, materials=mats, spec=spec, body={"span": 0.05, "wing": "butterfly", "antenna": "clubbed"})


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 6) for v in c] + [1.0]


def sick_mi(horn_recipe, out, seed=SEED, w=512):
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    lo, hi = horn_recipe["predicted"]["bounds_min"], horn_recipe["predicted"]["bounds_max"]
    # side projection: u along UE Y (= -Blender y, nose->tail), v along UE Z (up); cm
    umin, usize = round(-hi[1] * 100, 2), round((hi[1] - lo[1]) * 100, 2); vmin, vsize = round(lo[2] * 100, 2), round((hi[2] - lo[2]) * 100, 2)
    rng = np.random.default_rng(seed); y, x = np.mgrid[0:w, 0:w] / w
    coat = np.zeros((w, w))
    for _ in range(28):
        cx, cy, r = rng.uniform(0.1, 0.9), rng.uniform(0.35, 0.85), rng.uniform(0.03, 0.09)
        coat = np.maximum(coat, np.clip(1 - np.hypot(x - cx, y - cy) / r, 0, 1) ** 0.6)
    coat *= np.clip((y - 0.3) / 0.1, 0, 1)                       # image row 0 = top (v=1): patches on the back/flank, not the legs
    hoof = np.clip(1 - np.abs(y - 0.95) / 0.05, 0, 1) * (0.6 + 0.4 * (rng.random((w, w)) > 0.5))
    files = {}
    for k, a in (("CoatMask", np.flipud(coat)), ("LesionMask", np.flipud(hoof))):
        fn = "T_%s_Sick_%s.png" % (HORN, k); p = os.path.join(out, fn)
        Image.fromarray(np.round(np.clip(a, 0, 1) * 255).astype(np.uint8), "L").save(p, optimize=True)
        files[k] = {"file": fn, "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
    P = {"CoatTint": "7A6A52", "PatchColour": "B8A88A", "LesionColour": "6A2A22"}
    man = {"schema": "bb-material-variants/1", "asset": HORN, "gap": "G172 (pythagoras 50449)", "status": "NOT READY", "style": "G28: MI params + masks, no baked textures",
           "parent_material": {"name": "M_Hornback (UE side)", "graph": "hide: BaseColor = lerp(CoatTint, PatchColour, CoatMask(uv) * PatchAmount); hoof: BaseColor = lerp(hoof, LesionColour, LesionMask(uv) * LesionAmount)"},
           "projection": {"uv": "u = (LocalPosition.Y - u.min)/u.size, v = (LocalPosition.Z - v.min)/v.size (PreSkinnedLocalPosition)", "u": {"axis": "Y", "min_cm": umin, "size_cm": usize}, "v": {"axis": "Z", "min_cm": vmin, "size_cm": vsize}},
           "masks": files,
           "instances": {"MI_Mob_Lab_Hornback_Sick": {"slots": {"0": "hide", "2": "hoof"}, "params": {**{k: {"srgb_hex": v, "linear_rgba": lin(v)} for k, v in P.items()}, "PatchAmount": 0.85, "LesionAmount": 1.0, "Roughness": 0.97,
                                                       "CoatMask": files["CoatMask"]["file"], "LesionMask": files["LesionMask"]["file"]}},
                         "MI_Mob_Lab_Hornback_Healthy": {"slots": {"0": "hide", "2": "hoof"}, "params": {"CoatTint": {"srgb_hex": "8A6A4A", "linear_rgba": lin("8A6A4A")}, "PatchAmount": 0.0, "LesionAmount": 0.0, "Roughness": 0.9}}}}
    with open(os.path.join(out, "MI_Mob_Lab_Hornback_Sick.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1); f.write("\n")
    return man


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", required=True); ap.add_argument("--masks"); o = ap.parse_args()
    for m in (hare(), shoal(), fritillary()):
        p = os.path.join(o.out_dir, "mob_%s.quad.json" % m["asset"])
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(m, f, indent=1); f.write("\n")
        print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"], list(m["clips"]))
    if o.masks:
        hb = json.load(open(os.path.join(HERE, "..", "..", "..", "data", "contest", "g03_hornback.quad.json"), encoding="utf-8"))
        print("sick MI", list(sick_mi(hb, o.masks)["masks"]))
