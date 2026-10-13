# SPDX-License-Identifier: MIT
"""Higher-quality Orrery Reach art, built in a cloud Blender (bpy) and shipped as glb + sent.json (ADR-058).

    python3 orr_hq.py <out folder> [--only N] [--names A,B,...] [--sheet sheet.png]

It's the same catalogue and the same shapes as orr_build.py, with these upgrades:
- **Smoother curves:** cylinders, rings and rods get twice the segments (at least 12); spheres get one more subdivision.
- **Bevelled boxes:** every box edge is rounded (2 segments), so planks, crates and walls catch the light.
- **Smooth shading:** split at 35 degrees, so curves are smooth and hard corners stay crisp.
- **Real materials:**
    - brass, star and gear parts are metallic;
    - water, glass and lens parts are glossy;
    - wood, soil and stone are rough.
If an asset's upgraded version is over the art queue's triangle budget, it's rebuilt one step down (bevels and
segments only); if that's still over, the plain version ships. Every glb is checked against its own report with the
judge's Blender = file checks before it's kept.

Output is `<out>/<Kind>/<Asset>.glb` and `<Asset>.sent.json`, ready for `bot-team\\art\\<Kind>\\` and a READY row.
"""
import json
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
import orr_build  # noqa: E402
from asset_pipeline import glb, ship, sides  # noqa: E402

BUDGET = {"Tool": 3000, "Item": 3000, "Wpn": 3000, "Prop": 3000, "Mob": 6000, "Veh": 12000, "Bld": 15000, "Sky": 15000}
LEVEL = {"value": 2}   # 2 = full upgrade, 1 = bevels + fewer segments, 0 = plain orr_build

_box, _cyl, _ball, _ring, _strut, _finish, _mat = (orr_build.Part.box, orr_build.Part.cyl, orr_build.Part.ball,
                                                    orr_build.Part.ring, orr_build.Part.strut, orr_build.Part.finish,
                                                    orr_build.mat)


def _seg(seg, lo):
    return seg if LEVEL["value"] == 0 else max(seg * LEVEL["value"], lo if LEVEL["value"] == 2 else seg)


def box(self, loc, size, mi=0, rot=(0, 0, 0)):
    if LEVEL["value"] == 0:
        return _box(self, loc, size, mi, rot)
    before = set(self.bm.faces)
    r = bmesh.ops.create_cube(self.bm, size=1.0)
    self._place(r["verts"], loc, rot, size)
    verts = set(r["verts"])
    edges = [e for e in self.bm.edges if e.verts[0] in verts and e.verts[1] in verts]
    off = min(abs(s) for s in size) * 0.18
    if off > 0.0005:
        bmesh.ops.bevel(self.bm, geom=edges, offset=off, offset_type="OFFSET", segments=2 if LEVEL["value"] == 2 else 1,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    self.bm.faces.ensure_lookup_table()
    self._tag([f for f in self.bm.faces if f not in before], mi)


def cyl(self, loc, r, h, mi=0, seg=8, r2=None, rot=(0, 0, 0)):
    return _cyl(self, loc, r, h, mi, _seg(seg, 12), r2, rot)


def ball(self, loc, r, mi=0, sub=1, scale=(1, 1, 1)):
    return _ball(self, loc, r, mi, min(sub + (1 if LEVEL["value"] == 2 else 0), 3), scale)


def ring(self, loc, R, r, mi=0, seg=16, rot=(0, 0, 0)):
    return _ring(self, loc, R, r, mi, _seg(seg, 16), rot)


def strut(self, a, b, r, mi=0, seg=6):
    return _strut(self, a, b, r, mi, _seg(seg, 10))


def finish(self, coll):
    ob = _finish(self, coll)
    if LEVEL["value"]:
        me = ob.data
        for p in me.polygons:
            p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(35))
    return ob


METAL = ("brass", "star", "gear", "bell", "lens_rim", "iron", "metal", "copper", "gold", "silver")
GLOSS = ("water", "glass", "lens", "ice", "crystal", "heart", "glow")
ROUGH = ("wood", "soil", "stone", "clay", "wool", "roof", "leaf", "straw", "rope")


def mat(name, rgb, emit=0.0):
    m = _mat(name, rgb, emit)
    if LEVEL["value"]:
        b = m.node_tree.nodes.get("Principled BSDF")
        n = name.lower()
        if any(t in n for t in METAL):
            b.inputs["Metallic"].default_value, b.inputs["Roughness"].default_value = 0.85, 0.3
        elif any(t in n for t in GLOSS):
            b.inputs["Metallic"].default_value, b.inputs["Roughness"].default_value = 0.0, 0.12
        elif any(t in n for t in ROUGH):
            b.inputs["Roughness"].default_value = 0.85
    return m


orr_build.Part.box, orr_build.Part.cyl, orr_build.Part.ball = box, cyl, ball
orr_build.Part.ring, orr_build.Part.strut, orr_build.Part.finish, orr_build.mat = ring, strut, finish, mat


def tris_now(asset):
    coll = bpy.data.collections.get(asset)
    total = 0
    for o in coll.objects if coll else []:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            total += len(o.data.loop_triangles)
    return total


def export(asset, kind, out):
    path = os.path.join(out, kind, asset + ".glb")
    coll = bpy.data.collections[asset]
    env = {"PARAMS": json.dumps({"path": path, "objects": [o.name for o in coll.objects if o.type == "MESH"]})}
    # The scene holds only this asset (a fresh factory scene per asset). Headless bpy has no selection context for
    # the exporter, so use_selection exports nothing (a 132-byte glb); export the whole scene instead.
    exec(sides.BLENDER_EXPORT.replace("use_selection=True", "use_selection=False"), env)
    sent = env["result"]
    witness = glb.summarize(path)
    checks = [c for c in ship.judge(sent, witness, {"meshes": [], "materials": []}) if "Blender" in c["check"]]
    bad = [c for c in checks if not c["ok"]]
    with open(os.path.join(out, kind, asset + ".sent.json"), "w") as f:
        json.dump(sent, f, indent=1)
    return sent, bad


def build_one(asset, kind, family, p, out):
    for level in (2, 1, 0):
        LEVEL["value"] = level
        bpy.ops.wm.read_factory_settings(use_empty=True)
        orr_build.build(asset, kind, family, p)
        t = tris_now(asset)
        if t <= BUDGET[kind]:
            break
    sent, bad = export(asset, kind, out)
    return {"asset": asset, "kind": kind, "level": level, "tris": t, "bad": [b["check"] for b in bad]}


def main(argv):
    out = argv[0]
    only = int(argv[argv.index("--only") + 1]) if "--only" in argv else None
    names = argv[argv.index("--names") + 1].split(",") if "--names" in argv else None
    items = orr_build.catalogue()
    if names:
        items = [i for i in items if i[0] in names]
    if only:
        items = items[:only]
    rows = []
    for asset, kind, family, p in items:
        rows.append(build_one(asset, kind, family, p, out))
        r = rows[-1]
        if r["bad"] or len(rows) % 50 == 0:
            print("%4d %s level %d tris %d %s" % (len(rows), asset, r["level"], r["tris"], r["bad"] or "ok"), flush=True)
    with open(os.path.join(out, "hq-report.json"), "w") as f:
        json.dump(rows, f, indent=1)
    levels = [r["level"] for r in rows]
    bad = [r for r in rows if r["bad"]]
    print("ORR HQ %d built: full %d, reduced %d, plain %d; judge failures %d" % (
        len(rows), levels.count(2), levels.count(1), levels.count(0), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
