# SPDX-License-Identifier: MIT
"""Tests for choir_groove.py (G53). python test_choir_groove.py [--d2 <Daedalus2 checkout at/after 77814390>]"""
import argparse, json, os, re, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import choir_groove as C
KIT = os.path.join(HERE, "..", "..", "..", "data", "contest", "ytm_g53.kit.json")
ok = fail = 0


def t(name, cond, info=""):
    global ok, fail
    ok, fail = (ok + 1, fail) if cond else (ok, fail + 1)
    if not cond:
        print("FAIL", name, info)


ap = argparse.ArgumentParser(); ap.add_argument("--d2"); o = ap.parse_args()
kit = json.load(open(KIT, encoding="utf-8")); M = C.build(kit); A = {a["asset"]: a for a in kit["assets"]}
d = tempfile.mkdtemp(); p, M2 = C.write(KIT, d); t("write == build", M2 == M); t("deterministic", C.build(kit) == M)
t("schema", M["schema"] == "bb-material-variants/1"); t("states", M["states"] == ["Quiet", "Humming"])
V = {v["state"]: v["params"] for v in M["variants"]}
t("same params both MIs", set(V["Quiet"]) == set(V["Humming"]) == set(M["params"]))
t("quiet is dark", V["Quiet"]["EmissiveStrength"]["value"] == 0 and V["Quiet"]["PulseDepth"]["value"] == 0)
t("humming glows and pulses", V["Humming"]["EmissiveStrength"]["value"] > 0 and V["Humming"]["PulseRate"]["value"] > 0)
for st in M["states"]:
    for k in ("GrooveBase", "EmissiveColour"):
        t("%s %s linear" % (st, k), len(V[st][k]["linear_rgba"]) == 4 and all(0 <= c <= 1 for c in V[st][k]["linear_rgba"]))
    t(st + " ranges", 0 <= V[st]["PulseDepth"]["value"] <= 1 and 0 <= V[st]["Roughness"]["value"] <= 1)
t("groove slot is the kit's M1", A[C.STONE]["materials"][1]["name"] == M["stone"]["groove_slot"] and A[C.STONE]["materials"][1]["glow"])
t("only groove parts on the groove slot", all(q["name"].startswith(("Groove", "Note")) == (q["slot"] == 1) for q in A[C.STONE]["objects"][0]["parts"]))
t("stone sockets", sorted(s["name"] for s in A[C.STONE]["sockets"]) == sorted(M["stone"]["sockets"]))
t("lookup 2 states x 3 ranges", len(M["lookup"]) == 6)
t("brighter with range", M["lookup"]["Humming/range1"]["emissive_strength"] < M["lookup"]["Humming/range2"]["emissive_strength"] < M["lookup"]["Humming/range3"]["emissive_strength"])
t("quiet ignores range", {M["lookup"]["Quiet/range%d" % r]["emissive_strength"] for r in (1, 2, 3)} == {0.0})
t("tier -> range", M["tier_range"] == {"1": 1, "2": 2, "3": 2, "4": 3})
B = M["bridge"]["states"]
t("bridge states 3/2/1/0", sorted(B) == ["0", "1", "2", "3"] and all(B[s]["mesh"] in A for s in B))
t("crossable iff strength > 0", all(B[s]["crossable"] == (int(s) > 0) for s in B))
t("collision iff crossable", all(B[s]["collision"] == B[s]["crossable"] for s in B))
t("intact swap in place (same sockets)", B["3"]["socket_A"] == B["2"]["socket_A"] == B["1"]["socket_A"] and B["3"]["socket_B"] == B["2"]["socket_B"] == B["1"]["socket_B"])
t("2 m segments", all(abs(B[s]["socket_B"][0] - B[s]["socket_A"][0] - 2.0) < 1e-9 for s in B))
t("anchor socket at deck", M["bridge"]["anchor"]["socket"][2] == B["3"]["socket_A"][2])
if o.d2:
    j = os.path.join(o.d2, "daedalus-core", "src", "main", "java", "com", "daedalus", "world", "brew", "stones")
    cs = open(os.path.join(j, "ChoirStones.java"), encoding="utf-8").read(); bl = open(os.path.join(j, "BridgeLedger.java"), encoding="utf-8").read()
    t("MAX_STRENGTH = 3", re.search(r"MAX_STRENGTH\s*=\s*3\s*;", bl) is not None)
    body = cs[cs.index("public static int range(int tier)"):]; body = body[:body.index("\n    }")]
    t("range() mentions T1 1, T4 3", "T1 1" in cs and "T4 3" in cs, body[:200])
print("%d/%d" % (ok, ok + fail)); sys.exit(1 if fail else 0)
