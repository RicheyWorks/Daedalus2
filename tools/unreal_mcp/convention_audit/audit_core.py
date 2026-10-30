"""Engine-free rules for the headless production-convention audit (Epic P1 candidate 3).

The editor side (a PythonScriptCommandlet run on an ISOLATED copy in a disposable project,
inside the custodian's window, never alongside the live editor and never on DaedalusRealm)
only has to export one fact row per asset. This module judges those rows and writes the
audit, so the rules are testable without Unreal.

Fact row: {"path": "/Game/X/Prop_A", "class": "StaticMesh", "name": "Prop_A",
           "slots": ["M_BB_Wood_01"], "simple_collision": 1, "bounds_cm": [x, y, z],
           "no_collision_ok": false}
"""
import hashlib
import json
import os
import re

SCHEMA = "daedalus.convention_audit.v1"
DEFAULT_KINDS = ("Prop", "Mob", "Item", "Tool", "Bld", "Wpn", "Decal")
CLASS_PREFIX = {"StaticMesh": None, "Material": "M", "MaterialInstanceConstant": "MI",
                "Texture2D": "T", "SkeletalMesh": None}
MIN_CM = 1.0
MAX_CM = 10000.0
_BAD_SLOT = re.compile(r"(\.\d{3}$)|[#\s]|[^A-Za-z0-9_]")


def _name_ok(name, cls, kinds):
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name or ""):
        return False
    prefix = CLASS_PREFIX.get(cls)
    if prefix:
        return name.startswith(prefix + "_") and len(name) > len(prefix) + 1
    head = name.split("_", 1)
    return len(head) == 2 and bool(head[1]) and (head[0] in kinds or head[0] == "SM")


def check_row(row, kinds=DEFAULT_KINDS):
    findings = []
    name = row.get("name", "")
    cls = row.get("class", "")
    if not _name_ok(name, cls, kinds):
        findings.append("name")
    for slot in row.get("slots") or []:
        if not isinstance(slot, str) or not slot or _BAD_SLOT.search(slot):
            findings.append("slot_name:%s" % slot)
    if cls == "StaticMesh":
        coll = row.get("simple_collision")
        if not isinstance(coll, int) or isinstance(coll, bool):
            findings.append("collision_unknown")
        elif coll == 0 and not row.get("no_collision_ok"):
            findings.append("no_simple_collision")
        bounds = row.get("bounds_cm")
        if not (isinstance(bounds, list) and len(bounds) == 3
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in bounds)):
            findings.append("bounds_unknown")
        else:
            largest = max(abs(v) for v in bounds)
            if largest < MIN_CM or largest > MAX_CM:
                findings.append("bounds_out_of_range")
    return findings


def audit(rows, kinds=DEFAULT_KINDS):
    if not rows:
        return {"schema": SCHEMA, "count": 0, "verdict": "FAIL", "reason": "no assets audited", "flagged": []}
    flagged = []
    for row in rows:
        found = check_row(row, kinds)
        if found:
            flagged.append({"path": row.get("path", ""), "findings": found})
    return {"schema": SCHEMA, "count": len(rows), "verdict": "PASS" if not flagged else "FLAGGED",
            "flagged": flagged}


def folder_digest(root):
    """sha256 over relative paths + bytes, for the before/after 'nothing was written' proof."""
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            digest.update(rel.encode("utf-8") + b"\0")
            with open(full, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def unchanged(before, after):
    return before == after


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(audit(json.load(handle)), indent=2))
