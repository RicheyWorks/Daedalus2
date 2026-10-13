# SPDX-License-Identifier: MIT
"""Combat asset handoff on hand-made .glb files: no Blender, no Unreal (the importer is a fake).

    python harness/combat_handoff_test.py      # n/m last; exit 1 on any failure
"""
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from asset_pipeline import combat_handoff as ch  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%-4s  %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  " + str(detail)))


def write(path, meshes=(), empties=(), joints=None):
    """meshes: [(name, tris)]; empties: node names without a mesh; joints: names made into one skin."""
    acc, ms, nodes = [], [], []
    for name, tris in meshes:
        acc.append({"count": tris * 3, "type": "VEC3", "componentType": 5126, "min": [0, 0, 0], "max": [1, 1, 1]})
        ms.append({"name": name, "primitives": [{"attributes": {"POSITION": len(acc) - 1}}]})
        nodes.append({"name": name, "mesh": len(ms) - 1})
    for e in empties:
        nodes.append({"name": e})
    doc = {"asset": {"version": "2.0"}, "accessors": acc, "meshes": ms, "nodes": nodes}
    if joints:
        first = len(nodes)
        nodes += [{"name": j} for j in joints]
        doc["skins"] = [{"joints": list(range(first, first + len(joints)))}]
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 20 + len(body)) + struct.pack("<I4s", len(body), b"JSON") + body)


SPEC_PATH = os.path.join(HERE, "specs", "combat-slice-1.json")
spec = ch.load_spec(SPEC_PATH)
JOINTS = ["root", "pelvis", "head", "hand_r"] + ["b%d" % i for i in range(20)]
d = tempfile.mkdtemp()
os.makedirs(os.path.join(d, "glb"))


def good_slice():
    write(os.path.join(d, "glb", "Wpn_Slice1_Rifle.glb"), [("Rifle", 9000)],
          ["SOCKET_Muzzle", "SOCKET_Grip", "SOCKET_Sight", "Magazine"])
    for n in ("Guard", "Scout", "Brute"):
        write(os.path.join(d, "glb", "Enemy_Slice1_%s.glb" % n),
              [("Body_LOD0", 20000), ("Body_LOD1", 8000), ("Body_LOD2", 2000)], joints=JOINTS)
    write(os.path.join(d, "Env_Slice1_Arena.glb"),
          [("Arena", 100000)] + [("UCX_Arena_%02d" % i, 12) for i in range(4)])


# 1. the shipped spec is the first combat slice: 1 weapon, 3 enemies, 1 environment
check("spec: combat-slice-1 is 1 weapon + 3 enemies + 1 environment",
      [a["role"] for a in spec["assets"]].count("enemy") == 3 and len(spec["assets"]) == 5)

# 2. a good slice passes, checked only (nothing imported)
good_slice()
calls = []


def fake_import(asset, path, dest, unreal):
    calls.append((asset["name"], dest))
    return {"ok": True, "dest": dest + "/" + asset["name"], "checks": []}


r = ch.run(spec, d, importer=fake_import)
check("good slice: PASS without import", r["verdict"] == "PASS" and not calls,
      [(a["name"], [c for c in a["checks"] if not c["ok"]]) for a in r["assets"]])

# 3. with --import, each passing asset goes to <dest>/<Role>
out = os.path.join(d, "out")
r = ch.run(spec, d, out, do_import=True, importer=fake_import)
check("import: all 5 imported under the slice dest by role",
      len(calls) == 5 and ("Enemy_Slice1_Scout", "/Game/Daedalus/Combat/Slice1/Enemy") in calls, calls)
check("report: report.json + REPORT.md written",
      json.load(open(os.path.join(out, "report.json")))["verdict"] == "PASS"
      and "| Env_Slice1_Arena | environment | PASS |" in open(os.path.join(out, "REPORT.md")).read())

# 4. weapon missing a socket fails, and is not imported
write(os.path.join(d, "glb", "Wpn_Slice1_Rifle.glb"), [("Rifle", 9000)], ["SOCKET_Muzzle", "SOCKET_Grip", "SOCKET_Sight"])
calls.clear()
r = ch.run(spec, d, do_import=True, importer=fake_import)
w = r["assets"][0]
check("weapon: missing Magazine socket FAILs and names it",
      w["verdict"] == "FAIL" and any(c["check"] == "socket Magazine" and not c["ok"] for c in w["checks"]), w)
check("weapon: a failing asset is never imported", "Wpn_Slice1_Rifle" not in [c[0] for c in calls], calls)
check("slice: one failure fails the slice", r["verdict"] == "FAIL")
good_slice()

# 5. enemy: no skin, too few joints, missing joint, gaps in LODs, LOD not lighter
p = os.path.join(d, "glb", "Enemy_Slice1_Guard.glb")
a = spec["assets"][1]
write(p, [("Body_LOD0", 20000), ("Body_LOD1", 8000), ("Body_LOD2", 2000)])
check("enemy: no skeleton FAILs", not ch.check_asset(a, p)["ok"])
write(p, [("Body_LOD0", 20000), ("Body_LOD1", 8000), ("Body_LOD2", 2000)], joints=["root", "pelvis", "head"])
res = ch.check_asset(a, p)
check("enemy: 3 joints < 20 and no hand_r both FAIL",
      {c["check"] for c in res["checks"] if not c["ok"]} == {"skeleton joints >= 20", "joint hand_r"}, res["checks"])
write(p, [("Body_LOD0", 20000), ("Body_LOD2", 2000)], joints=JOINTS)
check("enemy: LOD0 + LOD2 (gap) FAILs the LOD check",
      any(c["check"].startswith("LODs") and not c["ok"] for c in ch.check_asset(a, p)["checks"]))
write(p, [("Body_LOD0", 20000), ("Body_LOD1", 25000), ("Body_LOD2", 2000)], joints=JOINTS)
check("enemy: LOD1 heavier than LOD0 FAILs",
      any(c["check"] == "each LOD lighter than the last" and not c["ok"] for c in ch.check_asset(a, p)["checks"]))
write(p, [("Body_LOD0", 70000), ("Body_LOD1", 8000), ("Body_LOD2", 2000)], joints=JOINTS)
check("enemy: over max_triangles FAILs",
      any(c["check"] == "triangles <= 60000" and not c["ok"] for c in ch.check_asset(a, p)["checks"]))

# 6. environment: too few hulls, or only collision
e = spec["assets"][4]
pe = os.path.join(d, "Env_Slice1_Arena.glb")
write(pe, [("Arena", 1000), ("UCX_Arena_01", 12)])
check("environment: 1 hull < 4 FAILs", not ch.check_asset(e, pe)["ok"])
write(pe, [("UCX_A_%d" % i, 12) for i in range(4)])
check("environment: collision only (no render mesh) FAILs", not ch.check_asset(e, pe)["ok"])
good_slice()

# 7. missing or broken files, and the bridge going away
os.remove(os.path.join(d, "glb", "Enemy_Slice1_Brute.glb"))
r = ch.run(spec, d)
check("missing glb: FAIL 'glb on disk'", r["assets"][3]["checks"][0]["check"] == "glb on disk" and not r["ok"])
with open(os.path.join(d, "glb", "Enemy_Slice1_Brute.glb"), "wb") as f:
    f.write(b"not a glb at all")
r = ch.run(spec, d)
check("broken glb: FAIL 'glb readable', no crash", r["assets"][3]["checks"][0]["check"] == "glb readable"
      and not r["assets"][3]["ok"])
good_slice()


def down(*_):
    raise ConnectionRefusedError("Unreal bridge 9877 closed")


r = ch.run(spec, d, do_import=True, importer=down)
check("bridge down: assets FAIL with the import error, run finishes",
      all(not a["ok"] and "9877" in a["import"]["error"] for a in r["assets"]))

# 8. spec validation and reuse
for bad, why in (({"schema": "x", "assets": [{}]}, "schema"),
                 ({"schema": ch.SCHEMA, "assets": []}, "no assets"),
                 ({"schema": ch.SCHEMA, "assets": [{"name": "A", "role": "vehicle"}]}, "role"),
                 ({"schema": ch.SCHEMA, "assets": [{"name": "A", "role": "weapon"}] * 2}, "twice"),
                 ({"schema": ch.SCHEMA, "expect": {"enemy": 3}, "assets": [{"name": "A", "role": "enemy"}]}, "expects")):
    try:
        ch.load_spec(bad)
        check("spec: rejects (%s)" % why, False)
    except ch.SpecError as ex:
        check("spec: rejects (%s)" % why, why in str(ex), ex)
ch.ROLES["prop"] = lambda doc, s: [ch._check("prop has a mesh", bool(doc.get("meshes")))]
write(os.path.join(d, "Crate.glb"), [("Crate", 12)])
r = ch.run({"schema": ch.SCHEMA, "slice": "s2", "assets": [{"name": "Crate", "role": "prop"}]}, d)
check("reuse: a later slice adds a role without touching the harness", r["verdict"] == "PASS"
      and r["dest"] == "/Game/Daedalus/Combat/s2")
del ch.ROLES["prop"]
check("cli: exit 0 on the good slice", ch.main(["--spec", SPEC_PATH, "--folder", d]) == 0)
shutil.rmtree(d)

n = sum(results)
print("%d/%d" % (n, len(results)))
sys.exit(0 if n == len(results) else 1)
