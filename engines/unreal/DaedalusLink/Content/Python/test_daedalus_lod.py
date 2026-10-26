# SPDX-License-Identifier: MIT
"""Offline test of daedalus_lod: the Python BBA 1 parser/writer/selector against blender-team's C++ parity file
(asset_lod_parity.txt: 40 manifests, 240 selections, 20 refusals), plus Unreal's screen-size maths.
Run: python test_daedalus_lod.py"""
import os
import tempfile

import daedalus_lod as d

HERE = os.path.dirname(os.path.abspath(__file__))
PARITY = os.path.join(HERE, "..", "..", "..", "core-test", "asset_lod_parity.txt")


def unescape(s):
    return s.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")


def test():
    ok = total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    cases = canon_ok = sel_ok = sels = bads = bad_ok = 0
    assets = None
    with open(PARITY, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("raw\t"):
                assets, err = d.parse(unescape(line[4:]))
                cases += 1
            elif line.startswith("canon\t"):
                canon_ok += assets is not None and d.write(assets) == unescape(line[6:])
            elif line.startswith("sel "):
                _, i, dist, lod = line.split()
                sels += 1
                sel_ok += assets is not None and d.select(assets[int(i)], int(dist)) == int(lod)
            elif line.startswith("bad\t"):
                _, text, want = line.split("\t", 2)
                got, err = d.parse(unescape(text))
                bads += 1
                bad_ok += got is None and err == want
                if not (got is None and err == want):
                    print("   bad mismatch:", repr(text), "want", want, "got", err)
    check("40 manifests parse and write canonically like C++", cases == 40 and canon_ok == 40)
    check("240 selections match", sels == 240 and sel_ok == 240)
    check("20 refusals with the same messages", bads == 20 and bad_ok == 20)

    # Unreal's screen size: 90 degree horizontal FOV, 16:9 -> 1.778 r / d
    check("screen size at 20 radii is about 0.0889", abs(d.screen_size(100, 2000) - 0.08889) < 1e-4)
    check("closer is bigger, clamped to 1", d.screen_size(100, 1000) > d.screen_size(100, 2000) and d.screen_size(100, 1) == 1.0)

    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "Rock_LOD1.glb"), "wb").close()
        man, _ = d.parse("BBA 1\nasset Rock lod0 100 lod1 60 radius 100 switch 2000\nasset Tree lod0 50 lod1 30 radius 50 switch 1000\n"
                         "asset Hut lod0 10 lod1 - radius 300 switch 6000\nasset Far lod0 9 lod1 5 radius 1 switch 500\n")
        acts = {a["id"]: a for a in d.actions(man, tmp, {"Rock": ("/Game/BB/Rock", 1), "Tree": ("/Game/BB/Tree", 2),
                                                         "Hut": ("/Game/BB/Hut", 1)})}
        check("missing LOD1 is imported from <id>_LOD1.glb", acts["Rock"]["do"] == "import LOD1 + screen size")
        check("a mesh that has LOD1 only gets its screen size", acts["Tree"]["do"] == "screen size"
              and abs(acts["Tree"]["lod1_screen_size"] - 0.0889) < 1e-3)
        check("no LOD1 in the manifest: skipped", acts["Hut"]["do"] == "skip")
        check("assets with no mesh in the folder are left out", "Far" not in acts)
    print("%d/%d" % (ok, total))
    return ok == total


if __name__ == "__main__":
    raise SystemExit(0 if test() else 1)
