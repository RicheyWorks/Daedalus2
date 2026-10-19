# SPDX-License-Identifier: MIT
"""Prop_PracticeCrate recipe (blender-team): the UNREAL-ONBOARDING section 9 practice prop as pure data, in the same
manifest format tools/blender/weapons/build_rifle.py builds (bevelled boxes, palette slots, SOCKET_ empties).
Spec: unreal-epic-boss link 48146, request_id ueb-practice-crate-20261019.
Metres, Blender Z up, front -Y, origin at the bottom centre; glTF export is +Y up: Blender (x, y, z) -> glTF (x, z, -y).
Usage: python crate_recipe.py --manifest data/practice/Prop_PracticeCrate.recipe.json
Build: blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest <that> --out <staging>"""
import argparse, hashlib, json

ASSET = "Prop_PracticeCrate"
SPEC = {"request_id": "ueb-practice-crate-20261019", "link": 48146, "tri_cap": 500, "sockets": ["Top"],
        "size_m": [0.52, 0.52, 0.5], "palette": ["wood", "dark"], "lod": "LOD0 only", "collision": "none", "seed": 0}
PALETTE = {"wood": "9A6B3F", "dark": "4A4D57"}      # copied from blender-harness bharness/palette.py
BOX_TRIS = 44                                        # cube with all 12 edges bevelled once (as rifle_recipe.py)


def box(name, size, centre, slot):
    return {"name": name, "shape": "box", "size": list(size), "centre": list(centre), "slot": slot, "tris": BOX_TRIS}


def recipe():
    parts = [box("Body", (0.5, 0.5, 0.5), (0, 0, 0.25), 0),
             box("BandLow", (0.52, 0.52, 0.06), (0, 0, 0.10), 1),
             box("BandHigh", (0.52, 0.52, 0.06), (0, 0, 0.40), 1)]
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
    m["recipe_sha256"] = hashlib.sha256(json.dumps({k: m[k] for k in ("materials", "parts", "sockets")}, sort_keys=True).encode()).hexdigest()
    return m


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--manifest", required=True); o = a.parse_args()
    with open(o.manifest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(recipe(), f, indent=1); f.write("\n")
    print(json.dumps(recipe()["predicted"]))
