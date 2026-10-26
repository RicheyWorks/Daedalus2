# SPDX-License-Identifier: MIT
"""Offline test of daedalus_ram_audit's maths. Run: python test_daedalus_ram_audit.py"""
import daedalus_ram_audit as a


def test():
    ok = total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    check("2048 DXT1 with mips = 2 MiB * 4/3", a.texture_bytes("2048x2048", "PF_DXT1") == int(2048 * 2048 * 0.5 * 4 / 3))
    check("2048 BC7 is twice DXT1", abs(a.texture_bytes("2048x2048", "PF_BC7") - 2 * a.texture_bytes("2048x2048", "PF_DXT1")) <= 8)
    check("uncompressed RGBA8 is 8x DXT1", abs(a.texture_bytes("1024x1024", "PF_B8G8R8A8") - 8 * a.texture_bytes("1024x1024", "PF_DXT1")) <= 8)
    check("unknown format counts as RGBA8 (the high side)", a.texture_bytes("64x64", "PF_Mystery") == a.texture_bytes("64x64", "PF_R8G8B8A8"))
    check("volume dims multiply", a.texture_bytes("32x32x32", "PF_G8", mips=False) == 32 ** 3)
    check("bad dims are 0, not an error", a.texture_bytes(None, "PF_DXT1") == 0 and a.texture_bytes("big", "PF_DXT1") == 0)
    check("mesh bytes from counts; junk is 0", a.mesh_bytes("1000", "2000") == 1000 * 32 + 2000 * 12 and a.mesh_bytes("x", 5) == 0)
    check("owner folder depth 1", a.owner("/Game/Claude/Art/Rock_T") == "/Game/Claude/" and a.owner("/Game/Tex") == "/Game/")
    check("owner folder depth 2", a.owner("/Game/Claude/Art/Rock_T", 2) == "/Game/Claude/Art/")
    check("non-/Game packages keep their root", a.owner("/DaedalusLink/M_Base") == "/DaedalusLink/")
    check("PF_ tag wins", a.pixel_format("PF_BC7", "TC_Normalmap", "True") == "PF_BC7")
    check("compression decides without PF_", a.pixel_format("TSF_BGRA8", "TC_Normalmap") == "PF_BC5"
          and a.pixel_format(None, "TC_Default", "True") == "PF_DXT5" and a.pixel_format(None, "TC_Default", "False") == "PF_DXT1")
    check("nothing known -> None (counted at RGBA8)", a.pixel_format(None, None, None) is None)
    rows = [{"package": "/Game/A/x", "kind": "texture", "bytes": 300}, {"package": "/Game/B/y", "kind": "mesh", "bytes": 500},
            {"package": "/Game/A/z", "kind": "mesh", "bytes": 250}, {"package": "/Game/C/w", "kind": "texture", "bytes": 1}]
    s = a.summarize(rows, top=2)
    check("owners largest first with kind split", [o["owner"] for o in s["owners"]] == ["/Game/A/", "/Game/B/", "/Game/C/"]
          and s["owners"][0]["texture_bytes"] == 300 and s["owners"][0]["mesh_bytes"] == 250 and s["owners"][0]["assets"] == 2)
    check("top N biggest assets", [r["package"] for r in s["biggest"]] == ["/Game/B/y", "/Game/A/x"] and s["total_bytes"] == 1051)
    print("%d/%d" % (ok, total))
    return ok == total


if __name__ == "__main__":
    raise SystemExit(0 if test() else 1)
