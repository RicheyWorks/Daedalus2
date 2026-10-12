# SPDX-License-Identifier: MIT
"""End to end: real Blender (bpy) exports, the Unreal stand-in imports, and the judge must be right both ways.

    python3 harness/e2e.py [--blender-connector DIR] [--unreal-connector DIR]

Starts both bridges on free ports, builds a small scene in Blender, ships it, and then makes the import lose
something five different ways. Each of those must be REJECTED by the check it breaks. Prints one line per
check and n/m last; exits 1 on any failure.
"""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from asset_pipeline import ship as S, wire  # noqa: E402


def _find(name, given):
    for d in ([given] if given else []) + [os.path.join(ROOT, "..", name), os.path.join(ROOT, "..", "..", "..", name),
                                           os.path.join(os.path.expanduser("~"), name)]:
        if d and os.path.isdir(d):
            return os.path.abspath(d)
    sys.exit("can't find %s; pass --%s DIR" % (name, name.replace("claude-", "")))


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(addr, proc, secs=90):
    end = time.time() + secs
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError("bridge exited early:\n" + proc.stdout.read().decode(errors="replace")[-3000:])
        if wire.reachable(addr, 0.5):
            return
        time.sleep(0.2)
    raise RuntimeError("bridge on %s never came up" % (addr,))


SCENE = r'''
import bpy
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
def mat(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.2, depth=3.0)
lamp = bpy.context.active_object; lamp.name = "Lamp"
lamp.data.materials.append(mat("Brass")); lamp.data.materials.append(mat("Glow"))
for poly in lamp.data.polygons:
    poly.material_index = 1 if poly.normal.z > 0.5 else 0
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(3, 0, 0))
crate = bpy.context.active_object; crate.name = "Crate"; crate.scale = (2, 1, 1)
crate.data.materials.append(mat("Wood"))
bev = crate.modifiers.new("Bevel", "BEVEL"); bev.width = 0.05; bev.segments = 2
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.5, location=(-3, 0, 0))
bpy.context.active_object.name = "Stone"
result = sorted(o.name for o in bpy.data.objects)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender-connector")
    ap.add_argument("--unreal-connector")
    a = ap.parse_args()
    bdir, udir = _find("claude-blender-connector", a.blender_connector), _find("claude-unreal-connector", a.unreal_connector)
    work = tempfile.mkdtemp(prefix="pipeline-e2e-")
    zpath = os.path.join(work, "claude_blender_bridge.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        src = os.path.join(bdir, "addon", "claude_blender_bridge", "__init__.py")
        z.write(src, "claude_blender_bridge/__init__.py")
    bport, uport = _port(), _port()
    blender = subprocess.Popen([sys.executable, os.path.join(bdir, "tests", "host.py"), zpath, str(bport), "600"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    unreal = subprocess.Popen([sys.executable, os.path.join(HERE, "standin_unreal.py"), udir, str(uport), "600"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    B, U = ("127.0.0.1", bport), ("127.0.0.1", uport)
    results = []

    def check(name, ok, detail=""):
        results.append(bool(ok))
        print("%-4s  %s%s" % ("ok" if ok else "FAIL", name, ("  " + str(detail)[:400]) if not ok else ""), flush=True)

    try:
        _wait(B, blender)
        _wait(U, unreal)
        names = wire.call(B, "execute_code", code=SCENE)["result"]
        check("Blender built the test scene", names == ["Crate", "Lamp", "Stone"], names)

        r = S.ship("Props", dest="/Game/Test", folder=work, blender=B, unreal=U)
        check("three objects ship, every check passes", r["ok"] and len(r["checks"]) == 10,
              [c for c in r["checks"] if not c["ok"]])
        crate = next(o for o in r["blender"]["objects"] if o["name"] == "Crate")
        check("the bevel modifier is applied before export (more than a cube's 12 triangles)",
              crate["triangles"] > 12, crate)
        check("object scale stays on the node: the crate's mesh is 1 m, not 2 m",
              abs(crate["dims"][0] - 1.0) < 0.05, crate["dims"])
        lamp = next(m for m in r["file"]["meshes"] if m["name"].startswith("Cylinder") or "Lamp" in m["name"])
        check("a two-material object is one mesh with two slots", sorted(lamp["materials"]) == ["Brass", "Glow"], lamp)
        stone = [m for m in r["unreal"]["meshes"] if len(m["materials"]) == 1 and m["materials"][0] == "-1"]
        check("a bare mesh gets Unreal's default slot and still passes", len(stone) == 1, r["unreal"]["meshes"])
        ucrate = next(m for m in r["unreal"]["meshes"] if m["name"] == "Crate")
        check("Unreal bakes the crate's 2x scale: 200 cm long, as seen live on UE 5.8.3",
              abs(ucrate["dims_cm"][0] - 200) < 2, ucrate)
        check("Unreal sizes are centimetres", any(m["dims_cm"][0] > 250 for m in r["unreal"]["meshes"]),
              r["unreal"]["meshes"])

        r_saved = wire.call(U, "pipeline.saved")
        saved = (r_saved.get("result") or r_saved).get("saved", r_saved)
        check("the import saves what it made (no 'Save Content?' left for the editor to ask on close)",
              "/Game/Test/Props" in saved, saved)
        r = S.ship("Crate", objects=["Crate"], dest="/Game/Test", folder=work, blender=B, unreal=U)
        check("one named object ships alone", r["ok"] and len(r["unreal"]["meshes"]) == 1, r["checks"])

        wire.call(U, "pipeline.fault", kind="nanite")
        r = S.ship("Props", dest="/Game/Nanite", folder=work, blender=B, unreal=U)
        nan = [m for m in r["unreal"]["meshes"] if m.get("nanite")]
        check("Nanite's simplified fallback doesn't fail an intact import (the pickaxes, 440 vs 422)",
              r["ok"] and nan and any(m["render_triangles"] < m["triangles"] for m in nan),
              [c for c in r["checks"] if not c["ok"]] or r["unreal"]["meshes"])

        canaries = {"drop_mesh": "every file mesh became an Unreal static mesh",
                    "drop_tris": "triangles: file = Unreal, mesh by mesh",
                    "drop_slot": "material slots: file = Unreal, mesh by mesh",
                    "scale_m": "sizes: file (m) = Unreal (cm)",
                    "no_materials": "Unreal made a material for each one used",
                    "engine_parent": "every material is ready for Nanite (on the project's base, not the engine plugin's)"}
        for kind, broke in canaries.items():
            wire.call(U, "pipeline.fault", kind=kind)
            r = S.ship("Props", dest="/Game/Canary", folder=work, blender=B, unreal=U)
            failed = [c["check"] for c in r["checks"] if not c["ok"]]
            check("canary %s is REJECTED by '%s'" % (kind, broke), not r["ok"] and broke in failed, failed)

        try:
            S.ship("Ghost", objects=["NoSuchThing"], folder=work, blender=B, unreal=U)
            check("a missing Blender object is an error naming it", False, "shipped")
        except wire.BridgeError as e:
            check("a missing Blender object is an error naming it", e.side == "Blender" and "NoSuchThing" in str(e), e)

        try:
            S.ship("Props", folder=work, blender=B, unreal=("127.0.0.1", _port()))
            check("an unreachable Unreal is an OSError, not a hang", False, "shipped")
        except OSError:
            check("an unreachable Unreal is an OSError, not a hang", True)

        rep = os.path.join(work, "report.json")
        code = S.main(["--name", "Cli", "--objects", "Lamp", "--folder", work, "--dest", "/Game/Test",
                       "--blender-port", str(bport), "--unreal-port", str(uport), "--report", rep])
        check("the command line ships and writes its report (exit 0)", code == 0 and os.path.getsize(rep) > 0, code)
        wire.call(U, "pipeline.fault", kind="drop_tris")
        code = S.main(["--name", "Cli", "--objects", "Lamp", "--folder", work,
                       "--blender-port", str(bport), "--unreal-port", str(uport)])
        check("the command line exits 1 when the judge rejects", code == 1, code)
    finally:
        for p in (blender, unreal):
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
    print("%d/%d" % (sum(results), len(results)))
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
