# SPDX-License-Identifier: MIT
"""Combat asset handoff: check a combat slice's Blender art against its spec, import what passes, report PASS/FAIL.

A slice spec (combat-slice/v1 JSON) lists each asset with a role. Each role has its own checks, read from the
.glb itself (no 3D library, no editor):

  weapon       named sockets (empty nodes SOCKET_<Name>, or a node named <Name>), so muzzle flash, grip and sights attach
  enemy        a skin (skeleton) with enough joints and the joints the animations need, plus LOD0..LODn meshes
               (<mesh>_LOD<n>), each LOD lighter than the one before
  environment  collision meshes (UCX_/UBX_/USP_/UCP_ prefixes, Unreal's convention), so the fight can hit and react

Every role can also set max_triangles. Assets that pass are imported through the pipeline's land() step (the same
judge the art queue uses); failing assets are never imported. The result is report.json plus REPORT.md.

    python -m asset_pipeline.combat_handoff --spec specs/combat-slice-1.json --folder <art dir> --out <dir> [--import]

Later slices reuse this unchanged: write a new spec, or add a role to ROLES.
"""
import argparse
import json
import os
import re
import sys
import time

from . import glb

SCHEMA = "combat-slice/v1"
COLLISION = ("UCX_", "UBX_", "USP_", "UCP_")
LOD_RE = re.compile(r"^(.*)_LOD(\d+)$", re.I)


class SpecError(ValueError):
    pass


def _node_names(doc):
    return [n.get("name", "node_%d" % i) for i, n in enumerate(doc.get("nodes", []))]


def _check(name, ok, detail=""):
    return {"check": name, "ok": bool(ok), "detail": detail}


def _tris(doc):
    return sum(glb._prim_tris(doc, p) for m in doc.get("meshes", []) for p in m.get("primitives", []))


def check_weapon(doc, spec):
    names = _node_names(doc)
    have = {n[7:] if n.upper().startswith("SOCKET_") else n for n in names}
    out = []
    for s in spec.get("sockets", ["Muzzle", "Grip"]):
        out.append(_check("socket %s" % s, s in have, "" if s in have else "no node SOCKET_%s" % s))
    return out


def check_enemy(doc, spec):
    names = _node_names(doc)
    skins = doc.get("skins", [])
    sk = spec.get("skeleton", {})
    out = [_check("skeleton present", bool(skins), "" if skins else "no skin in the glb (export the armature)")]
    joints = [names[j] for j in skins[0].get("joints", [])] if skins else []
    need = sk.get("min_joints", 1)
    out.append(_check("skeleton joints >= %d" % need, len(joints) >= need, "%d joints" % len(joints)))
    for j in sk.get("required_joints", []):
        out.append(_check("joint %s" % j, j in joints, "" if j in joints else "missing"))
    lods = {}
    for m in doc.get("meshes", []):
        hit = LOD_RE.match(m.get("name", ""))
        if hit:
            lods[int(hit.group(2))] = lods.get(int(hit.group(2)), 0) + sum(
                glb._prim_tris(doc, p) for p in m.get("primitives", []))
    want = spec.get("lods", 2)
    levels = sorted(lods)
    contiguous = levels == list(range(len(levels)))
    out.append(_check("LODs >= %d (LOD0..LOD%d)" % (want, want - 1), contiguous and len(levels) >= want,
                      "found %s" % (["LOD%d" % n for n in levels] or "none")))
    if len(levels) > 1:
        tris = [lods[n] for n in levels]
        out.append(_check("each LOD lighter than the last", all(a > b for a, b in zip(tris, tris[1:])), tris))
    return out


def check_environment(doc, spec):
    meshes = [m.get("name", "") for m in doc.get("meshes", [])]
    nodes = [n.get("name", "") for n in doc.get("nodes", []) if "mesh" in n]
    hulls = sorted({n for n in meshes + nodes if n.upper().startswith(COLLISION)})
    need = spec.get("collision", {}).get("min_hulls", 1)
    out = [_check("collision hulls >= %d" % need, len(hulls) >= need, "%d (%s)" % (len(hulls), ", ".join(hulls[:5])))]
    visible = [n for n in meshes if n and not n.upper().startswith(COLLISION)]
    out.append(_check("render mesh besides collision", bool(visible), "" if visible else "only collision meshes"))
    return out


ROLES = {"weapon": check_weapon, "enemy": check_enemy, "environment": check_environment}


def load_spec(path_or_dict):
    spec = path_or_dict
    if not isinstance(spec, dict):
        with open(path_or_dict, encoding="utf-8") as f:
            spec = json.load(f)
    if spec.get("schema") != SCHEMA:
        raise SpecError("spec schema is %r, want %r" % (spec.get("schema"), SCHEMA))
    assets = spec.get("assets") or []
    if not assets:
        raise SpecError("spec lists no assets")
    seen = set()
    for a in assets:
        if not a.get("name") or a.get("role") not in ROLES:
            raise SpecError("asset %r: needs a name and a role in %s" % (a.get("name"), sorted(ROLES)))
        if a["name"] in seen:
            raise SpecError("asset %s listed twice" % a["name"])
        seen.add(a["name"])
    for role, n in (spec.get("expect") or {}).items():
        got = sum(1 for a in assets if a["role"] == role)
        if got != n:
            raise SpecError("slice expects %d %s asset(s), spec lists %d" % (n, role, got))
    return spec


def find_glb(folder, asset):
    for rel in (asset.get("glb"), os.path.join("glb", asset["name"] + ".glb"), asset["name"] + ".glb"):
        if rel:
            p = rel if os.path.isabs(rel) else os.path.join(folder, rel)
            if os.path.exists(p):
                return p
    return None


def check_asset(asset, path):
    """{name, role, path, checks, ok} for one asset, from its glb alone."""
    res = {"name": asset["name"], "role": asset["role"], "path": path, "checks": []}
    if not path:
        res["checks"].append(_check("glb on disk", False, "no %s.glb in the art folder" % asset["name"]))
    else:
        try:
            doc = glb.read_json(path)
        except (ValueError, OSError) as e:
            doc = None
            res["checks"].append(_check("glb readable", False, str(e)[:160]))
        if doc is not None:
            res["checks"].append(_check("glb readable", True))
            res["checks"] += ROLES[asset["role"]](doc, asset)
            if asset.get("max_triangles"):
                t = _tris(doc)
                res["checks"].append(_check("triangles <= %d" % asset["max_triangles"], t <= asset["max_triangles"], t))
    res["ok"] = all(c["ok"] for c in res["checks"])
    return res


def pipeline_import(asset, path, dest, unreal=None):
    """Import through ship.land (the art queue's judge). Needs Unreal's bridge; tests pass their own importer."""
    from . import ship, wire
    w = glb.summarize(path)
    objects = [{"name": n["name"], "triangles": w["meshes"][n["mesh"]]["triangles"],
                "materials": w["meshes"][n["mesh"]]["materials"], "dims": w["meshes"][n["mesh"]]["dims"]}
               for n in w["nodes"]]
    report = {"name": asset["name"], "path": os.path.abspath(path), "started": time.time(), "source": "glb",
              "blender": {"objects": objects, "source": "combat handoff (glb as is)"}, "file": w, "exported_s": 0.0}
    r = ship.land(report, dest, True, unreal or wire.UNREAL)
    return {"ok": r["ok"], "dest": r["dest"], "checks": r["checks"]}


def run(spec, folder, out=None, do_import=False, importer=pipeline_import, unreal=None):
    spec = load_spec(spec)
    dest = spec.get("dest", "/Game/Daedalus/Combat/" + spec.get("slice", "slice"))
    results = []
    for asset in spec["assets"]:
        r = check_asset(asset, find_glb(folder, asset))
        if do_import and r["ok"]:
            try:
                r["import"] = importer(asset, r["path"], dest + "/" + asset["role"].title(), unreal)
            except Exception as e:   # a bridge problem is not the asset's fault, but the slice is not handed off
                r["import"] = {"ok": False, "error": str(e)[:200]}
            r["ok"] = r["ok"] and r["import"]["ok"]
        r["verdict"] = "PASS" if r["ok"] else "FAIL"
        results.append(r)
    report = {"schema": SCHEMA + "-report", "slice": spec.get("slice"), "dest": dest, "imported": do_import,
              "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "ok": all(r["ok"] for r in results), "assets": results}
    report["verdict"] = "PASS" if report["ok"] else "FAIL"
    if out:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        with open(os.path.join(out, "REPORT.md"), "w", encoding="utf-8") as f:
            f.write(markdown(report))
    return report


def markdown(report):
    lines = ["# Combat slice %s: %s" % (report["slice"], report["verdict"]), "",
             "%s, %s into %s" % (report["at"], "imported" if report["imported"] else "checked only (no import)",
                                 report["dest"]), "", "| Asset | Role | Verdict | Failed checks |", "|---|---|---|---|"]
    for a in report["assets"]:
        bad = [c["check"] + (" (%s)" % c["detail"] if c["detail"] else "") for c in a["checks"] if not c["ok"]]
        if a.get("import") and not a["import"]["ok"]:
            bad.append("import: %s" % a["import"].get("error", "judge failed"))
        lines.append("| %s | %s | %s | %s |" % (a["name"], a["role"], a["verdict"], "; ".join(bad) or "-"))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--folder", required=True, help="art folder holding the .glb files (or glb\\<name>.glb)")
    ap.add_argument("--out", help="write report.json and REPORT.md here")
    ap.add_argument("--import", dest="do_import", action="store_true", help="import passing assets into Unreal")
    a = ap.parse_args(argv)
    try:
        r = run(a.spec, a.folder, a.out, a.do_import)
    except SpecError as e:
        print("SPEC  %s" % e)
        return 2
    sys.stdout.write(markdown(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
