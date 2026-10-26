# SPDX-License-Identifier: MIT
"""What is missing for a combat slice: a plain to-do list for blender-team, per asset, from the spec + the art folder.

For each asset in a combat-slice/v1 spec it says MISSING (no .glb yet), FIX (a .glb exists but fails checks: each failure
comes with how to fix it in Blender) or READY, plus the asset's row in the art queue (QUEUE.md) when there is one. It never
imports anything and never touches Unreal or Blender; it only reads the spec, the folder and QUEUE.md.

    python -m asset_pipeline.combat_report --spec specs/combat-slice-1.json --folder <art dir> [--queue QUEUE.md] [--out <dir>]

Writes TODO-FOR-BLENDER-TEAM.md and todo.json into --out. Exit 0 when the whole slice is READY, 1 otherwise, 2 for a bad spec.
"""
import argparse
import json
import os
import re
import sys
import time

from . import combat_handoff as ch

HOW = [  # (regex on the failed check name, how to fix it in Blender)
    (r"^glb on disk", "Export {name}.glb (glTF Binary, +Y up, Apply Modifiers) to {glb}."),
    (r"^glb readable", "Re-export as glTF Binary (.glb); the file could not be read."),
    (r"^socket (\w+)", "Add an Empty named SOCKET_{g1} at the attach point, parented to the weapon, and export empties (not 'selected only')."),
    (r"^skeleton present", "Export with the armature and skinning on (glTF: Include > Armature / Skinning), one skin."),
    (r"^skeleton joints >= (\d+)", "Rig with at least {g1} bones in the exported armature."),
    (r"^joint (\w+)", "Name a bone exactly '{g1}' (the animations and sockets look it up by name)."),
    (r"^LODs >= (\d+)", "Add meshes named <Mesh>_LOD0 ... _LOD{n} in the same file, with no gaps in the numbering."),
    (r"^each LOD lighter", "Decimate so every LOD has fewer triangles than the one before it."),
    (r"^collision hulls >= (\d+)", "Add at least {g1} convex collision meshes named UCX_<Mesh>_NN (UBX_/USP_/UCP_ also work)."),
    (r"^render mesh besides collision", "Add the visible mesh; the file has only collision shapes."),
    (r"^triangles <= (\d+)", "Cut triangles to {g1} or fewer (Decimate, or remove hidden faces)."),
]


def howto(check, name, folder):
    for pat, text in HOW:
        m = re.match(pat, check["check"])
        if m:
            vals = {"name": name, "folder": folder, "glb": os.path.join(folder, "glb", name + ".glb")}
            for i, g in enumerate(m.groups(), 1):
                vals["g%d" % i] = g
            vals["n"] = max(0, int(m.group(1)) - 1) if m.groups() and m.group(1).isdigit() else 2
            return text.format(**vals)
    return "See the check '%s'." % check["check"]


def queue_rows(path):
    """{asset name: status cell} from the first Markdown table with Asset and Status columns."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    cols = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cols is None:
                low = [c.lower() for c in cells]
                if "asset" in low and "status" in low:
                    cols = (low.index("asset"), low.index("status"))
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if len(cells) > max(cols):
                out[cells[cols[0]]] = cells[cols[1]]
    return out


def build(spec, folder, queue_path=None):
    spec = ch.load_spec(spec)
    queue = queue_rows(queue_path)
    items = []
    for a in spec["assets"]:
        path = ch.find_glb(folder, a)
        res = ch.check_asset(a, path)
        failed = [c for c in res["checks"] if not c["ok"]]
        if not path:
            state = "MISSING"
        elif failed:
            state = "FIX"
        else:
            state = "READY"
        todo = [] if state == "READY" else [howto(c, a["name"], folder) for c in failed]
        items.append({"name": a["name"], "role": a["role"], "state": state, "glb": path, "queue": queue.get(a["name"]),
                      "todo": todo, "failed": [{"check": c["check"], "detail": c["detail"]} for c in failed]})
    counts = {s: sum(1 for i in items if i["state"] == s) for s in ("MISSING", "FIX", "READY")}
    return {"schema": "combat-slice/v1-todo", "slice": spec.get("slice"), "folder": folder, "dest": spec.get("dest"),
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "counts": counts, "ok": counts["MISSING"] + counts["FIX"] == 0,
            "queue_checked": bool(queue_path and os.path.exists(queue_path)), "assets": items,
            "spec_assets": {a["name"]: a for a in spec["assets"]}}


def requirement(a):
    r = {"weapon": "sockets " + ", ".join("SOCKET_" + s for s in a.get("sockets", ["Muzzle", "Grip"])),
         "enemy": "armature >= %d bones incl. %s; %d LODs (<Mesh>_LOD0..)" % (
             a.get("skeleton", {}).get("min_joints", 1), ", ".join(a.get("skeleton", {}).get("required_joints", [])) or "-", a.get("lods", 2)),
         "environment": ">= %d collision hulls (UCX_<Mesh>_NN) + a visible mesh" % a.get("collision", {}).get("min_hulls", 1)}.get(a["role"], a["role"])
    if a.get("max_triangles"):
        r += "; <= %d triangles" % a["max_triangles"]
    return r


def markdown(t):
    c = t["counts"]
    out = ["# Combat slice %s: what blender-team still owes" % t["slice"], "",
           "%s. **%d MISSING, %d to FIX, %d READY** of %d assets. Folder: `%s`." % (t["at"], c["MISSING"], c["FIX"], c["READY"], len(t["assets"]), t["folder"]),
           "Import into Unreal happens only after every check below passes, and only in a claimed editor turn.", "",
           "| Asset | Role | State | Art queue row | Must have |", "|---|---|---|---|---|"]
    for i in t["assets"]:
        q = i["queue"] if i["queue"] else ("(no row yet)" if t["queue_checked"] else "(queue not read)")
        out.append("| %s | %s | **%s** | %s | %s |" % (i["name"], i["role"], i["state"], q, requirement(t["spec_assets"][i["name"]])))
    for i in t["assets"]:
        if i["todo"]:
            out += ["", "## %s (%s)" % (i["name"], i["state"])] + ["- " + x for x in i["todo"]]
    out += ["", "Check it yourself (no editor needed): `python -m asset_pipeline.combat_handoff --spec specs/combat-slice-1.json --folder <art dir>`.",
            "Sample passing files and each defect: `python -m asset_pipeline.combat_fixtures --spec specs/combat-slice-1.json --out <dir>`.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--queue", help="art queue QUEUE.md, to show each asset's row")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        t = build(a.spec, a.folder, a.queue)
    except (ch.SpecError, OSError, ValueError) as e:
        print("SPEC  %s" % e)
        return 2
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "TODO-FOR-BLENDER-TEAM.md"), "w", encoding="utf-8") as f:
            f.write(markdown(t))
        slim = {k: v for k, v in t.items() if k != "spec_assets"}
        with open(os.path.join(a.out, "todo.json"), "w", encoding="utf-8") as f:
            json.dump(slim, f, indent=2)
    sys.stdout.write(markdown(t))
    return 0 if t["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())