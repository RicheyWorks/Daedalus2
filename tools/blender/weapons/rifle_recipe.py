# SPDX-License-Identifier: MIT
"""Wpn_Slice1_Rifle recipe (blender-team): the combat-slice-1 weapon as pure data. A seeded, deterministic list of
parts (bevelled boxes and cylinders), material slots and sockets. Building it needs no Blender, so it can be tested,
diffed and pinned in a manifest before anyone spends a Blender window. build_rifle.py turns the same recipe into
meshes inside Blender.

Conventions (authoritative sources, not new rules):
- combat-slice/v1 spec (connectors/claude-asset-pipeline/specs/combat-slice-1.json): <= 40,000 triangles; sockets
  Muzzle, Grip, Sight, Magazine as empty nodes SOCKET_<Name>.
- bot-team art/BRIEF.md: metres (1 unit = 1 m), origin at the bottom centre, front toward -Y in Blender, 1 to 3
  flat-colour material slots, Kind_Name naming. glTF export uses +Y up, so Blender (x, y, z) -> glTF (x, z, -y).
- Colours by name from blender-harness bharness/palette.py (resolved to hex in the manifest).
Usage: python rifle_recipe.py [--seed N] [--bharness <blender-harness dir>] --manifest <out.json>"""
import argparse, hashlib, json, os, random, sys

ASSET = "Wpn_Slice1_Rifle"
SPEC = {"max_triangles": 40000, "sockets": ["Muzzle", "Grip", "Sight", "Magazine"]}   # copied from combat-slice-1.json
DEFAULT_SEED = 1101
MATERIALS = ["dark", "steel", "starmetal"]        # slot 0 body, 1 metal, 2 accent (the brief's blaster styling)
GLOW_SLOTS = [2]
CYL_SEGMENTS = 16
BOX_TRIS = 44                                      # a cube with all 12 edges bevelled once: 6 + 12 quads + 8 corner tris
EXPORT = {"format": "GLB", "export_yup": True, "export_apply": True, "export_extras": True}


def cyl_tris(n=CYL_SEGMENTS):
    return 4 * n - 4                               # 2n side triangles + two n-gon caps of n - 2 triangles each


def box(name, size, centre, slot):
    return {"name": name, "shape": "box", "size": [round(v, 4) for v in size], "centre": [round(v, 4) for v in centre], "slot": slot, "tris": BOX_TRIS}


def cyl(name, radius, length, centre, slot):
    """Cylinder along Y (the barrel axis)."""
    return {"name": name, "shape": "cyl_y", "radius": round(radius, 4), "length": round(length, 4), "centre": [round(v, 4) for v in centre],
            "segments": CYL_SEGMENTS, "slot": slot, "tris": cyl_tris()}


def recipe(seed=DEFAULT_SEED):
    """-> dict(parts, sockets) in Blender metres, Z up, front -Y, origin at the bottom centre. Same seed, same recipe."""
    r = random.Random(seed)
    u = lambda a, b: round(r.uniform(a, b), 3)
    body_len, body_h, body_w = u(0.30, 0.36), u(0.10, 0.12), 0.07
    guard_len, barrel_len = u(0.18, 0.24), u(0.12, 0.18)
    stock_len, ribs = u(0.18, 0.22), r.randint(3, 6)
    z0 = 0.20                                          # body centre height before re-centring (grip and mag hang below)
    p = [box("Receiver", (body_w, body_len, body_h), (0, 0, z0), 0),
         box("Rail", (0.035, body_len * 0.9, 0.02), (0, 0, z0 + body_h / 2 + 0.01), 1)]
    yf = -body_len / 2                                 # receiver front face
    p.append(box("Handguard", (body_w * 0.9, guard_len, body_h * 0.75), (0, yf - guard_len / 2, z0 + 0.005), 0))
    for i in range(ribs):                              # vent ribs on the handguard, evenly spaced
        y = yf - guard_len * (i + 1) / (ribs + 1)
        p.append(box("Rib_%d" % i, (body_w * 0.96, 0.012, body_h * 0.55), (0, y, z0 + 0.005), 2 if i % 2 == 0 else 1))
    yb = yf - guard_len                                # handguard front face
    p.append(cyl("Barrel", 0.014, barrel_len, (0, yb - barrel_len / 2, z0 + 0.01), 1))
    p.append(cyl("MuzzleBrake", 0.022, 0.05, (0, yb - barrel_len - 0.025, z0 + 0.01), 1))
    p.append(box("FrontSight", (0.012, 0.015, 0.035), (0, yb + 0.02, z0 + body_h * 0.375 + 0.0175), 1))
    opt_len = u(0.10, 0.13); zr = z0 + body_h / 2 + 0.02
    p.append(box("OpticBody", (0.04, opt_len, 0.04), (0, -0.02, zr + 0.03), 0))
    p.append(box("OpticMount", (0.03, 0.03, 0.015), (0, -0.02, zr + 0.0075), 1))
    p.append(cyl("OpticLens", 0.016, 0.01, (0, -0.02 - opt_len / 2 - 0.005, zr + 0.03), 2))
    mag_h = u(0.12, 0.16)
    p.append(box("Magazine", (0.045, 0.07, mag_h), (0, -0.07, z0 - body_h / 2 - mag_h / 2), 1))
    p.append(box("MagBase", (0.05, 0.08, 0.015), (0, -0.07, z0 - body_h / 2 - mag_h - 0.0075), 0))
    grip_h = 0.12
    p.append(box("PistolGrip", (0.04, 0.05, grip_h), (0, 0.08, z0 - body_h / 2 - grip_h / 2), 0))
    p.append(box("TriggerGuard", (0.012, 0.07, 0.01), (0, 0.025, z0 - body_h / 2 - 0.045), 1))
    p.append(box("Trigger", (0.008, 0.008, 0.03), (0, 0.035, z0 - body_h / 2 - 0.02), 1))
    yr = body_len / 2                                  # receiver rear face
    p.append(box("Stock", (0.05, stock_len, body_h * 0.7), (0, yr + stock_len / 2, z0 - 0.005), 0))
    p.append(box("StockRidge", (0.03, stock_len * 0.8, 0.015), (0, yr + stock_len / 2, z0 + body_h * 0.35 + 0.0025), 2))
    p.append(box("ButtPad", (0.055, 0.02, body_h * 1.1), (0, yr + stock_len + 0.01, z0 - 0.015), 1))
    p.append(box("Strip", (body_w + 0.004, body_len * 0.5, 0.012), (0, 0, z0 - 0.02), 2))
    sockets = {"Muzzle": (0, yb - barrel_len - 0.05, z0 + 0.01),
               "Grip": (0, 0.08, z0 - body_h / 2 - grip_h / 2),
               "Sight": (0, -0.02 + opt_len / 2, zr + 0.03),
               "Magazine": (0, -0.07, z0 - body_h / 2)}
    # re-centre: origin at the bottom centre of the bounding box (as the brief and tools.py do)
    lo, hi = bounds(p)
    off = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    for q in p:
        q["centre"] = [round(q["centre"][k] - off[k], 4) for k in range(3)]
    socks = [{"name": "SOCKET_" + n, "location": [round(sockets[n][k] - off[k], 4) for k in range(3)], "forward": [0, -1, 0]} for n in SPEC["sockets"]]
    for s in socks:   # held-prop attach sockets (UEB 48793/48810): sidecar +X along the barrel (Blender -Y), +Z up; Magazine stays plain
        if s["name"] in ("SOCKET_Muzzle", "SOCKET_Grip", "SOCKET_Sight"):
            s["attach"] = {"barrel": [0, -1, 0], "up": [0, 0, 1]}
    return {"asset": ASSET, "seed": seed, "parts": p, "sockets": socks}


def extent(q):
    if q["shape"] == "box":
        return [s / 2 for s in q["size"]]
    return [q["radius"], q["length"] / 2, q["radius"]]


def bounds(parts):
    lo = [min(q["centre"][k] - extent(q)[k] for q in parts) for k in range(3)]
    hi = [max(q["centre"][k] + extent(q)[k] for q in parts) for k in range(3)]
    return lo, hi


def to_gltf(v):
    """Blender Z-up (x, y, z) -> glTF +Y-up (x, z, -y), what the +Y-up export writes."""
    return [v[0], v[2], -v[1] if v[1] else 0.0]


def load_palette(bharness):
    sys.path.insert(0, bharness)
    from bharness import palette   # noqa: E402  (the existing colour library)
    return palette


def manifest(seed, bharness, source_bytes):
    rc = recipe(seed)
    pal = load_palette(bharness)
    lo, hi = bounds(rc["parts"])
    tris = sum(q["tris"] for q in rc["parts"])
    inside = all(all(lo[k] - 1e-6 <= s["location"][k] <= hi[k] + 1e-6 for k in range(3)) for s in rc["sockets"])
    checks = {"triangles <= %d" % SPEC["max_triangles"]: tris <= SPEC["max_triangles"],
              "sockets " + "/".join(SPEC["sockets"]): [s["name"] for s in rc["sockets"]] == ["SOCKET_" + n for n in SPEC["sockets"]],
              "sockets inside bounds": inside, "material slots 1..3": 1 <= len(MATERIALS) <= 3,
              "origin at bottom centre": abs(lo[2]) < 1e-6 and abs(lo[0] + hi[0]) < 1e-6 and abs(lo[1] + hi[1]) < 1e-6}
    return {"schema": "bb-recipe/1", "asset": ASSET, "status": "SOURCE-ONLY: recipe staged, not built, not exported, not READY",
            "seed": seed, "recipe_sha256": hashlib.sha256(source_bytes.replace(b"\r\n", b"\n")).hexdigest(),
            "spec": {"file": "connectors/claude-asset-pipeline/specs/combat-slice-1.json", **SPEC},
            "units": "metres; Blender Z up, front -Y, origin bottom centre; glTF export +Y up",
            "materials": [{"slot": i, "name": "%s_M%d" % (ASSET, i), "palette": m, "hex": pal.resolve(m), "glow": i in GLOW_SLOTS} for i, m in enumerate(MATERIALS)],
            "parts": rc["parts"], "sockets": [dict(s, location_gltf=to_gltf(s["location"])) for s in rc["sockets"]],
            "predicted": {"triangles": tris, "parts": len(rc["parts"]), "bounds_min": [round(v, 4) for v in lo], "bounds_max": [round(v, 4) for v in hi],
                          "dimensions": [round(hi[k] - lo[k], 4) for k in range(3)]},
            "checks": checks, "export": EXPORT,
            "build": "blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest <this file> --out <staging dir outside art/>  (needs a coordinated window)"}


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("--seed", type=int, default=DEFAULT_SEED)
    a.add_argument("--bharness", default=os.environ.get("BHARNESS", r"C:\Users\730ri\projects\blender-harness"))
    a.add_argument("--manifest", required=True)
    o = a.parse_args(argv)
    m = manifest(o.seed, o.bharness, open(os.path.abspath(__file__), "rb").read())
    os.makedirs(os.path.dirname(os.path.abspath(o.manifest)), exist_ok=True)
    with open(o.manifest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    print(json.dumps({"asset": ASSET, "seed": o.seed, "triangles": m["predicted"]["triangles"], "dimensions": m["predicted"]["dimensions"], "checks": m["checks"]}))
    return 0 if all(m["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
