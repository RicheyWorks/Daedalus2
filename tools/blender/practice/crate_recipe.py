# SPDX-License-Identifier: MIT
"""Prop_PracticeCrate recipe (blender-team): the UNREAL-ONBOARDING section 9 practice prop as pure data, in the same
manifest format tools/blender/weapons/build_rifle.py builds (bevelled boxes, palette slots, SOCKET_ empties).
Spec: unreal-epic-boss link 48146, request_id ueb-practice-crate-20261019.
Metres, Blender Z up, front -Y, origin at the bottom centre; glTF export is +Y up: Blender (x, y, z) -> glTF (x, z, -y).
Variants (InterchangeTests fixture, link 48353 grok-epic-speedup-20261019; the base recipe is unchanged):
  A: base + UCX_Prop_PracticeCrate, an unbevelled convex box (8 verts, 12 tris) parented to the mesh, covering the bounds.
  B: the same asset name with changed source geometry for the reimport/identity check: + a top band (LidBand) and two
     front/back plank seams; same materials, socket and pivot; tris and bounds change; UCX resized to the new bounds.
Usage: python crate_recipe.py [--variant A|B] --manifest data/practice/Prop_PracticeCrate[.A|.B].recipe.json
Build: blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest <that> --out <staging>"""
import argparse, hashlib, json

ASSET = "Prop_PracticeCrate"
SPEC = {"request_id": "ueb-practice-crate-20261019", "link": 48146, "tri_cap": 500, "sockets": ["Top"],
        "size_m": [0.52, 0.52, 0.5], "palette": ["wood", "dark"], "lod": "LOD0 only", "collision": "none", "seed": 0}
PALETTE = {"wood": "9A6B3F", "dark": "4A4D57"}      # copied from blender-harness bharness/palette.py
BOX_TRIS = 44                                        # cube with all 12 edges bevelled once (as rifle_recipe.py)


def box(name, size, centre, slot):
    return {"name": name, "shape": "box", "size": list(size), "centre": list(centre), "slot": slot, "tris": BOX_TRIS}


VARIANTS = ("A", "B")
UCX_TRIS = 12                                        # unbevelled cube


def recipe(variant=None):
    if variant not in (None,) + VARIANTS:
        raise ValueError("variant must be None, 'A' or 'B'")
    parts = [box("Body", (0.5, 0.5, 0.5), (0, 0, 0.25), 0),
             box("BandLow", (0.52, 0.52, 0.06), (0, 0, 0.10), 1),
             box("BandHigh", (0.52, 0.52, 0.06), (0, 0, 0.40), 1)]
    if variant == "B":
        parts += [box("LidBand", (0.52, 0.52, 0.04), (0, 0, 0.48), 1),
                  box("SeamFront", (0.04, 0.03, 0.38), (0, -0.25, 0.25), 1),
                  box("SeamBack", (0.04, 0.03, 0.38), (0, 0.25, 0.25), 1)]
    mats = [{"slot": i, "name": "%s_M%d" % (ASSET, i), "palette": p, "hex": PALETTE[p], "glow": False}
            for i, p in enumerate(SPEC["palette"])]
    sockets = [{"name": "SOCKET_Top", "location": [0.0, 0.0, 0.5], "forward": [0, -1, 0], "location_gltf": [0.0, 0.5, 0.0]}]
    lo = [min(p["centre"][i] - p["size"][i] / 2 for p in parts) for i in range(3)]
    hi = [max(p["centre"][i] + p["size"][i] / 2 for p in parts) for i in range(3)]
    m = {"schema": "blender-recipe/v1", "asset": ASSET, "status": "RECIPE (staged, not READY)", "spec": SPEC,
         "units": "metres, Blender Z up, front -Y, origin bottom centre; glTF +Y up",
         "materials": mats, "parts": parts, "sockets": sockets,
         "predicted": {"triangles": sum(p["tris"] for p in parts), "parts": len(parts),
                       "bounds_min": [round(v, 4) for v in lo], "bounds_max": [round(v, 4) for v in hi],
                       "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)]},
         "export": {"format": "GLB", "export_yup": True, "export_apply": True, "export_extras": True},
         "build": "blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest <this> --out <staging dir outside art>"}
    keys = ("materials", "parts", "sockets")
    if variant:
        size = m["predicted"]["dimensions"]
        m["variant"] = variant
        m["fixture"] = {"for": "InterchangeTests (unreal-epic-boss, link 48353)", "request_id": "grok-epic-speedup-20261019",
                        "base_glb_sha256": "b1453d459a26a767b6140bf2a0e17496325c3f1d932a916e98ce0516394538c3"}
        m["collision"] = [{"name": "UCX_" + ASSET, "shape": "box", "size": size,
                           "centre": [round((lo[i] + hi[i]) / 2, 4) for i in range(3)], "tris": UCX_TRIS, "convex": True}]
        m["predicted"]["collision_tris"] = UCX_TRIS
        m["status"] = "FIXTURE %s (staged, not READY)" % variant
        keys += ("collision",)
    m["recipe_sha256"] = hashlib.sha256(json.dumps({k: m[k] for k in keys}, sort_keys=True).encode()).hexdigest()
    return m


def delta(a, b):
    """B minus A: triangles and bounds (metres)."""
    pa, pb = a["predicted"], b["predicted"]
    return {"triangles": pb["triangles"] - pa["triangles"],
            "bounds_min": [round(pb["bounds_min"][i] - pa["bounds_min"][i], 4) for i in range(3)],
            "bounds_max": [round(pb["bounds_max"][i] - pa["bounds_max"][i], 4) for i in range(3)],
            "dimensions": [round(pb["dimensions"][i] - pa["dimensions"][i], 4) for i in range(3)]}


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--manifest", required=True); a.add_argument("--variant", choices=VARIANTS)
    o = a.parse_args(); m = recipe(o.variant)
    with open(o.manifest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    print(json.dumps(m["predicted"]))
