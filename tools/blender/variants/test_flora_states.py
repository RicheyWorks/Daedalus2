# SPDX-License-Identifier: MIT
"""Tests for flora_states.py (G48). python test_flora_states.py [--glb-root <bot-team dir>] [--d2 <Daedalus2 checkout>]
--glb-root also opens every reused pythagoras glb and checks the named slot exists; --d2 checks FLORA against BeeBloom.Flora."""
import argparse, json, os, re, struct, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import flora_states as F
KIT = os.path.join(HERE, "..", "..", "..", "data", "contest", "bee_g48.kit.json")
ok = fail = 0


def t(name, cond, info=""):
    global ok, fail
    ok, fail = (ok + 1, fail) if cond else (ok, fail + 1)
    if not cond:
        print("FAIL", name, info)


def glb_mats(p):
    b = open(p, "rb").read(); n = struct.unpack_from("<I", b, 12)[0]
    return [m.get("name") for m in json.loads(b[20:20 + n]).get("materials", [])]


ap = argparse.ArgumentParser(); ap.add_argument("--glb-root"); ap.add_argument("--d2"); o = ap.parse_args()
kit = json.load(open(KIT, encoding="utf-8")); M = F.build(kit)
d = tempfile.mkdtemp(); p, M2 = F.write(KIT, d); t("write == build", M2 == M); t("deterministic", F.build(kit) == M)
t("schema", M["schema"] == "bb-material-variants/1")
t("flora order = enum", M["flora_order"] == ["WILLOW_CATKIN", "CROCUS", "CLOVER", "BRAMBLE", "HEATHER"])
t("2 states", M["states"] == ["BLOOM", "FROST"])
names = {v["name"] for v in M["variants"]}
t("one MI per role x state", len(names) == len(F.ROLE) * 2 == len(M["variants"]))
for v in M["variants"]:
    P = v["params"]
    t(v["name"] + " params", set(P) == set(M["params"]))
    t(v["name"] + " bloom = identity" if v["state"] == "BLOOM" else v["name"] + " frost visible",
      (P["FrostAmount"]["value"] == 0 and P["RimeAmount"]["value"] == 0) if v["state"] == "BLOOM" else P["FrostAmount"]["value"] > 0.2)
    t(v["name"] + " ranges", all(0 <= P[k]["value"] <= 1 for k in ("FrostAmount", "FrostRoughness", "RimeAmount")))
    t(v["name"] + " linear tint", len(P["FrostTint"]["linear_rgba"]) == 4 and all(0 <= c <= 1 for c in P["FrostTint"]["linear_rgba"]))
A = {a["asset"]: a for a in kit["assets"]}
for f, E in M["flora"].items():
    t(f + " band", E["band"] in ("WETLAND", "MEADOW", "SCRUB"))
    t(f + " slots <= 3, MIs exist", 1 <= len(E["slots"]) <= 3 and all(s["mi"][st] in names for s in E["slots"] for st in M["states"]))
    t(f + " has a petal slot or is clover", any(s["role"] == "petal" for s in E["slots"]) or f == "CLOVER")
    t(f + " 8 plants on bed sockets", [q["socket"] for q in E["plants"]] == [s["name"] for s in A[F.BED]["sockets"]])
    t(f + " plants use own meshes", all(q["mesh"] in {m["mesh"] for m in E["meshes"]} for q in E["plants"]))
    if f in F.NEW:
        a = F.NEW[f][0]; t(f + " new slots = kit materials", [s["slot"] for s in E["slots"]] == [m["name"] for m in A[a]["materials"]])
    else:
        t(f + " reuses 10 PYT meshes", len(E["meshes"]) == 10 and all("pythagoras" in m["owner"] for m in E["meshes"]))
        t(f + " neighbours differ", all(E["plants"][i]["mesh"] != E["plants"][i + 1]["mesh"] for i in range(7)))
        if o.glb_root:
            for m in E["meshes"]:
                gp = os.path.join(o.glb_root, *m["mesh_path"].split("/"))
                t(m["mesh"] + " exists", os.path.isfile(gp), gp)
                if os.path.isfile(gp):
                    t(m["mesh"] + " has slot " + E["slots"][0]["slot"], glb_mats(gp)[E["slots"][0]["slot_index"]] == E["slots"][0]["slot"], glb_mats(gp))
t("lookup complete", len(M["lookup"]) == sum(len(E["slots"]) for E in M["flora"].values()) * 2 and set(M["lookup"].values()) <= names)
if o.d2:
    src = open(os.path.join(o.d2, "daedalus-core", "src", "main", "java", "com", "daedalus", "world", "battlefield", "BeeBloom.java"), encoding="utf-8").read()
    body = src[src.index("enum Flora"):]; body = body[:body.index(";")]
    t("FLORA = BeeBloom.Flora", re.findall(r"\b([A-Z_]+)\(", body) == F.FLORA, re.findall(r"\b([A-Z_]+)\(", body))
    t("bands = BeeBloom", all(re.search(r"%s\([^)]*Vegetation\.%s\)" % (f, F.BAND[f]), body) for f in F.FLORA))
print("%d/%d" % (ok, ok + fail)); sys.exit(1 if fail else 0)
