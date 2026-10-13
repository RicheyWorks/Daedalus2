# SPDX-License-Identifier: MIT
"""Ship Blender objects into Unreal and prove nothing was lost on the way.

    python -m asset_pipeline.ship --name Lamp --objects Lamp,Post --dest /Game/Daedalus/Props

1. Blender exports the objects to one .glb (modifiers applied) and reports what it sent: triangles,
   materials and size for each object.
2. The .glb is read here, with no 3D library. It is the witness between the two editors.
3. Unreal imports the .glb (Interchange) and reports what it made: static meshes with triangles,
   material slots and bounds, and the materials.
4. judge() compares Blender with the file, and the file with Unreal. Every check can fail. The report is
   written as JSON, and the exit code is 1 if any check failed.

Both editors must run on the same computer, because Unreal reads the file Blender wrote.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter

from . import glb, sides, wire

CM_PER_M = 100.0


def _close(a, b, rel=0.01, absolute=0.01):
    return abs(a - b) <= max(absolute, rel * max(abs(a), abs(b)))


def _dims_match(x, y, scale=1.0):
    return len(x) == len(y) and all(_close(a * scale, b) for a, b in zip(x, y))


def _same_sizes(xs, ys, scale=1.0):
    """Every size in xs pairs with its own size in ys, within tolerance. Sorting the lists and zipping them is not
    enough: float noise reorders near-ties (Mob_Realm_Party_Hero, 2026-10-12: two meshes 0.48 m long; Unreal said
    48.0 and 48.0000076 cm, so its sort swapped them, and a good asset was REJECTED for its sizes)."""
    if len(xs) != len(ys):
        return False
    free = list(ys)
    for a in sorted(xs, reverse=True):
        hit = next((i for i, b in enumerate(free) if _dims_match(a, b, scale)), None)
        if hit is None:
            return False
        free.pop(hit)
    return True


def judge(sent, witness, made):
    """[{check, ok, detail}] comparing Blender's report, the .glb summary and Unreal's report."""
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    nodes = witness["nodes"]
    meshes = witness["meshes"]
    by_node = [meshes[n["mesh"]] for n in nodes]

    # Blender -> file: one node for each exported object, and the same triangles, materials and size
    check("every Blender object reached the file", len(sent["objects"]) == len(nodes) and len(nodes) > 0,
          "%d objects, %d mesh nodes" % (len(sent["objects"]), len(nodes)))
    st = sum(o["triangles"] for o in sent["objects"])
    ft = sum(m["triangles"] for m in by_node)
    check("triangles: Blender = file", st == ft, "Blender %d, file %d" % (st, ft))
    sm = sorted({m for o in sent["objects"] for m in o["materials"]})
    fm = sorted({m for x in by_node for m in x["materials"]})
    check("materials: Blender = file", sm == fm, "Blender %s, file %s" % (sm, fm))
    sd = sorted(tuple(o["dims"]) for o in sent["objects"])
    fd = sorted(tuple(x["dims"]) for x in by_node)
    check("sizes: Blender = file", _same_sizes(sd, fd),
          "Blender %s, file %s" % (sd, fd))

    # file -> Unreal: Interchange makes one static mesh per node (named after it), with the node's scale baked
    # in, so Unreal is compared node by node: same triangles, slots and scaled size (m -> cm).
    um = made["meshes"]
    check("every file mesh became an Unreal static mesh", len(um) == len(nodes) and len(um) > 0,
          "file %d mesh nodes, Unreal %d static meshes" % (len(nodes), len(um)))
    want = Counter(m["triangles"] for m in by_node)
    got = Counter(m["triangles"] for m in um)
    check("triangles: file = Unreal, mesh by mesh", want == got,
          "file %s, Unreal %s" % (sorted(want.elements()), sorted(got.elements())))
    # a mesh with no material still gets one slot in Unreal (the default material)
    fslots = sorted(max(1, len(m["materials"])) for m in by_node)
    uslots = sorted(len(m["materials"]) for m in um)
    check("material slots: file = Unreal, mesh by mesh", fslots == uslots, "file %s, Unreal %s" % (fslots, uslots))
    fdims = sorted(tuple(n["dims"]) for n in nodes)
    udims = sorted(tuple(m["dims_cm"]) for m in um)
    sized = _same_sizes(fdims, udims, CM_PER_M)
    check("sizes: file (m) = Unreal (cm)", sized, "file %s m, Unreal %s cm" % (fdims, udims))
    used = {m for x in by_node for m in x["materials"]}
    check("Unreal made a material for each one used", len(made["materials"]) >= len(used),
          "used %d, Unreal made %d" % (len(used), len(made["materials"])))
    # ADR-055: a material left on the Interchange plugin's base has no Nanite usage, and a packaged game draws it
    # with the default material.
    engine = [m["name"] for m in made["materials"] if m.get("parent", "").startswith("/InterchangeAssets/")]
    check("every material is ready for Nanite (on the project's base, not the engine plugin's)", not engine,
          ", ".join(engine) or "all %d" % len(made["materials"]))
    return checks


# Unreal calls run directly on the editor's game thread (the bridge's unattended=False), never through Unreal's
# Remote Execution: that one channel is shared by every bot on the PC, and on 2026-10-12 a reply meant for one caller
# went to another and the watcher hung on it for 35 minutes. Import tasks are automated, so no modal dialog is
# raised. bridge_timeout makes the bridge give up instead of holding the call for its 30-minute default.
UNREAL_TIMEOUT = 300


def export(name, objects=None, folder=None, blender=wire.BLENDER, timeout=600):
    """The Blender half: the .glb, what Blender says it sent, and the file's own witness."""
    folder = folder or os.path.join(tempfile.gettempdir(), "daedalus-pipeline")
    path = os.path.abspath(os.path.join(folder, name + ".glb"))
    report = {"name": name, "path": path, "started": time.time()}
    report["blender"] = wire.obj(wire.call(blender, "execute_code", timeout=timeout, side="Blender",
                                           code=sides.script(sides.BLENDER_EXPORT, path=path, objects=objects or [])),
                                 "Blender", "the .glb export")
    report["file"] = glb.summarize(path)
    report["exported_s"] = round(time.time() - report["started"], 2)
    return report


def prebuilt(name, glb_path, sent):
    """The Blender half done elsewhere (a cloud Blender, ADR-058): a .glb and Blender's own report of what it sent
    (the same fields BLENDER_EXPORT reports), checked against the file's witness exactly as a live export is."""
    report = {"name": name, "path": os.path.abspath(glb_path), "started": time.time(), "blender": sent,
              "file": glb.summarize(glb_path), "exported_s": 0.0, "prebuilt": True}
    return report


def land(report, dest="/Game/Daedalus/Assets", save=True, unreal=wire.UNREAL, timeout=UNREAL_TIMEOUT):
    """The Unreal half: import the exported file, then judge all three sides."""
    report["dest"] = dest + "/" + report["name"]
    t = time.time()
    made = wire.call(unreal, "execute_python", timeout=timeout, side="Unreal", unattended=False,
                     bridge_timeout=timeout,
                     code=sides.script(sides.UNREAL_IMPORT, path=report["path"], dest=report["dest"], save=save))
    made = wire.obj(made, "Unreal", "the import")
    checks = judge(report["blender"], report["file"], made)
    report.update(ok=all(c["ok"] for c in checks), checks=checks, unreal=made, imported_s=round(time.time() - t, 2),
                  seconds=round(time.time() - report["started"], 2))
    return report


def ship(name, objects=None, dest="/Game/Daedalus/Assets", folder=None, save=True,
         blender=wire.BLENDER, unreal=wire.UNREAL, timeout=600):
    """Run the pipeline once and return its report (ok, checks, and what each side said)."""
    return land(export(name, objects, folder, blender, timeout), dest, save, unreal, min(timeout, UNREAL_TIMEOUT))


ship.export, ship.land, ship.prebuilt = export, land, prebuilt   # the watcher overlaps the halves: Blender exports the next asset while Unreal imports this one


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", required=True, help="asset name: the .glb file and the Unreal folder")
    ap.add_argument("--objects", default="", help="comma-separated Blender object names (default: visible meshes)")
    ap.add_argument("--dest", default="/Game/Daedalus/Assets")
    ap.add_argument("--folder", help="where the .glb is written (default: <temp>/daedalus-pipeline)")
    ap.add_argument("--report", help="write the JSON report here")
    ap.add_argument("--no-save", action="store_true", help="don't save the imported assets")
    ap.add_argument("--blender-port", type=int, default=wire.BLENDER[1])
    ap.add_argument("--unreal-port", type=int, default=wire.UNREAL[1])
    a = ap.parse_args(argv)
    try:
        r = ship(a.name, [o for o in a.objects.split(",") if o], a.dest, a.folder, not a.no_save,
                 (wire.BLENDER[0], a.blender_port), (wire.UNREAL[0], a.unreal_port))
    except (wire.BridgeError, OSError, ValueError) as e:
        print("FAIL  %s" % e)
        return 2
    for c in r["checks"]:
        print("%-4s  %-46s %s" % ("ok" if c["ok"] else "FAIL", c["check"], c["detail"]))
    print("%s  %s -> %s in %.1fs" % ("SHIPPED" if r["ok"] else "REJECTED", r["path"], r["dest"], r["seconds"]))
    if a.report:
        with open(a.report, "w") as f:
            json.dump(r, f, indent=2)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
