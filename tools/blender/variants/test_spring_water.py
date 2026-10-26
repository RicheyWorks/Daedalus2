# SPDX-License-Identifier: MIT
"""Pure-Python checks for spring_water.py. python test_spring_water.py [--java <SpringChain.java>] [--glb-root <bot-team dir>]"""
import json, os, re, struct, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spring_water as V
arg = lambda k, d: next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == k), d)
java = arg("--java", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "daedalus-core", "src", "main", "java", "com", "daedalus", "world", "brew", "story", "SpringChain.java"))
root = arg("--glb-root", None)
d = tempfile.mkdtemp(); p, m = V.write(d); p2, m2 = V.write(tempfile.mkdtemp()); checks = []
add = lambda n, ok: checks.append((n, bool(ok)))
if os.path.exists(java):
    src = open(java, encoding="utf-8").read(); names = re.findall(r'"([A-Z][A-Za-z ]+)"', src.split("String[] names = {", 1)[1].split("};", 1)[0])
    add("spring names/order = SpringChain.island()", names == V.SPRINGS)
    add("yield 4 + i/3 like SpringChain.island()", "4 + i / 3" in src and [s["yield"] for s in m["springs"].values()] == [4 + i // 3 for i in range(12)])
    add("ids spring_1..12 like SpringChain.island()", '"spring_" + (i + 1)' in src and list(m["springs"]) == ["spring_%d" % (i + 1) for i in range(12)])
else:
    add("SpringChain.java not found (skipped)", True)
add("deterministic (manifest + mask)", m == m2 and open(os.path.join(d, V.MASK), "rb").read() == open(os.path.join(os.path.dirname(p2), V.MASK), "rb").read())
add("12 springs, Homestead Well first on Prop_Well", len(m["springs"]) == 12 and m["springs"]["spring_1"]["name"] == "Homestead Well" and m["springs"]["spring_1"]["mesh"] == "Prop_Well" and m["springs"]["spring_1"]["first"])
add("springs 2-12 reuse AMF spring basins V1-V8", all(s["mesh"].startswith("Prop_Water_AMF_SpringBasin_V") for k, s in m["springs"].items() if k != "spring_1"))
add("repeated basins get a yaw offset", all(s["yaw_offset_deg"] != 0 for s in list(m["springs"].values())[9:]))
add("2 MIs (Cloudy, Clear), same param names", [v["name"] for v in m["variants"]] == ["MI_Spring_Water_Cloudy", "MI_Spring_Water_Clear"] and set(m["variants"][0]["params"]) == set(m["variants"][1]["params"]))
C, L = (v["params"] for v in m["variants"])
add("clear is clearer: less turbid, less opaque, smoother, SongClear 0 -> 1", C["Turbidity"]["value"] > L["Turbidity"]["value"] and C["Opacity"]["value"] > L["Opacity"]["value"] and C["Roughness"]["value"] > L["Roughness"]["value"] and (C["SongClear"]["value"], L["SongClear"]["value"]) == (0.0, 1.0))
add("cloudy reads silty (low saturation), clear reads blue", max(C["WaterShallow"]["linear_rgba"][:3]) - min(C["WaterShallow"]["linear_rgba"][:3]) < 0.12 and L["WaterShallow"]["linear_rgba"][2] > L["WaterShallow"]["linear_rgba"][0])
add("states map to SpringChain draws (raw_water / water)", [(v["spring_chain_clean"], v["draw_item"]) for v in m["variants"]] == [(False, "raw_water"), (True, "water")])
add("lookup = 12 springs x 2 states, all to real MIs", len(m["lookup"]) == 24 and set(m["lookup"].values()) == {v["name"] for v in m["variants"]})
add("linear values in 0..1", all(0 <= x <= 1 for v in m["variants"] for k in ("WaterShallow", "WaterDeep") for x in v["params"][k]["linear_rgba"]))
raw = open(os.path.join(d, V.MASK), "rb").read()
add("mask is an 8-bit greyscale PNG 256x256", raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[16:24] == bytes.fromhex("0000010000000100") and raw[24] == 8 and raw[25] == 0)
w, h, rows = V.silt_mask(); cov = sum(sum(1 for b in r if b > 127) for r in rows) / (w * h)
add("silt covers 25-60 %% (%.0f %%)" % (cov * 100), 0.25 <= cov <= 0.6)
seam = max(max(abs(rows[y][0] - rows[y][-1]) for y in range(h)), max(abs(rows[0][x] - rows[-1][x]) for x in range(w)))
add("mask tiles (edge step %d <= 24)" % seam, seam <= 24)
if root:
    for sid, s in m["springs"].items():
        g = os.path.join(root, *s["mesh_path"].split("/"))
        if not os.path.exists(g):
            add("%s mesh %s present" % (sid, g), False); continue
        b = open(g, "rb").read(); n = struct.unpack_from("<I", b, 12)[0]; J = json.loads(b[20:20 + n])
        add("%s %s water slot %s at index %d" % (sid, s["mesh"], s["water_slot"], s["water_slot_index"]), [x.get("name") for x in J["materials"]].index(s["water_slot"]) == s["water_slot_index"])
ok = 0
for n, r in checks:
    ok += r; print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
