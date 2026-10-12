# SPDX-License-Identifier: MIT
"""The judge on its own: one good shipment passes, and each way of breaking it fails the right check.

    python3 harness/judge_test.py        # n/m last; exit 1 on any failure
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from asset_pipeline.ship import judge  # noqa: E402

SENT = {"objects": [{"name": "Lamp", "triangles": 60, "materials": ["Brass", "Glow"], "dims": [3.0, 0.4, 0.4]},
                    {"name": "Stone", "triangles": 320, "materials": [], "dims": [1.0, 0.95, 0.95]}]}
FILE = {"materials": ["Brass", "Glow"],
        "meshes": [{"name": "Cylinder", "triangles": 60, "materials": ["Brass", "Glow"], "dims": [3.0, 0.4, 0.4]},
                   {"name": "Icosphere", "triangles": 320, "materials": [], "dims": [1.0, 0.95, 0.95]}],
        "nodes": [{"name": "Lamp", "mesh": 0}, {"name": "Stone", "mesh": 1}]}
MADE = {"meshes": [{"name": "SM_Cylinder", "triangles": 60, "materials": ["Brass", "Glow"], "dims_cm": [300.0, 40.0, 40.0]},
                   {"name": "SM_Icosphere", "triangles": 320, "materials": ["None"], "dims_cm": [100.0, 95.0, 95.0]}],
        "materials": [{"name": "MI_Brass"}, {"name": "MI_Glow"}]}

results = []


def failed(sent=SENT, file=FILE, made=MADE):
    return [c["check"] for c in judge(sent, file, made) if not c["ok"]]


def case(name, want, **kw):
    got = failed(**kw)
    ok = got == want
    results.append(ok)
    print("%-4s  %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  want %s, got %s" % (want, got)))


def bent(src, fn):
    d = copy.deepcopy(src)
    fn(d)
    return d


case("a good shipment passes every check", [])
case("Blender sent an object the file lacks", ["every Blender object reached the file", "sizes: Blender = file"],
     sent=bent(SENT, lambda d: d["objects"].append({"name": "Extra", "triangles": 0, "materials": [], "dims": [0, 0, 0]})))
case("export lost triangles", ["triangles: Blender = file"],
     sent=bent(SENT, lambda d: d["objects"][1].update(triangles=322)))
case("export lost a material", ["materials: Blender = file"],
     sent=bent(SENT, lambda d: d["objects"][0]["materials"].append("Rust")))
case("export changed a size", ["sizes: Blender = file"],
     sent=bent(SENT, lambda d: d["objects"][0].update(dims=[3.5, 0.4, 0.4])))
case("a size within 1% still matches", [],
     sent=bent(SENT, lambda d: d["objects"][0].update(dims=[3.02, 0.4, 0.4])))
case("Unreal lost a mesh", ["every file mesh became an Unreal static mesh", "triangles: file = Unreal, mesh by mesh",
                            "material slots: file = Unreal, mesh by mesh", "sizes: file (m) = Unreal (cm)"],
     made=bent(MADE, lambda d: d["meshes"].pop()))
case("Unreal lost a triangle", ["triangles: file = Unreal, mesh by mesh"],
     made=bent(MADE, lambda d: d["meshes"][0].update(triangles=59)))
case("triangles swapped between meshes still match (Unreal renames meshes)", [],
     made=bent(MADE, lambda d: d["meshes"].reverse()))
case("Unreal lost a slot", ["material slots: file = Unreal, mesh by mesh"],
     made=bent(MADE, lambda d: d["meshes"][0]["materials"].pop()))
case("a bare mesh with no slot at all in Unreal fails", ["material slots: file = Unreal, mesh by mesh"],
     made=bent(MADE, lambda d: d["meshes"][1].update(materials=[])))
case("Unreal kept metres", ["sizes: file (m) = Unreal (cm)"],
     made=bent(MADE, lambda d: [m.update(dims_cm=[x / 100 for x in m["dims_cm"]]) for m in d["meshes"]]))
case("Unreal made no materials", ["Unreal made a material for each one used"],
     made=bent(MADE, lambda d: d.update(materials=[])))
case("nothing shipped at all fails, it doesn't pass vacuously",
     ["every Blender object reached the file", "every file mesh became an Unreal static mesh"],
     sent={"objects": []}, file={"materials": [], "meshes": [], "nodes": []}, made={"meshes": [], "materials": []})

print("%d/%d" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
