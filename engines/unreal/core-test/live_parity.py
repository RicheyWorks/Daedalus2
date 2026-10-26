# SPDX-License-Identifier: MIT
"""
Live parity (ADR-032): read a running Daedalus world the way the Unreal plugin does - the package
manifest's palette, /chunks, then /chunk/blocks for each - and write it in the fixture format, with the
triangle count of the server's own world.glb. mesh_core_test then meshes it with DaedalusMeshCore.h and
must land on exactly that count.

    python3 live_parity.py http://localhost:8088 world-zero > live.mesh.txt && ./mesh_core_test live.mesh.txt
"""
import json
import struct
import sys
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main(server, world):
    base = server.rstrip("/") + "/api/v1/world/" + world
    manifest = json.loads(get(base + "/package/manifest"))
    glb = get(base + "/package/world.glb")
    jlen = struct.unpack_from("<I", glb, 12)[0]
    gltf = json.loads(glb[20:20 + jlen])
    # Index accessors are the SCALAR ones: count / 3 triangles each.
    tris = sum(a["count"] // 3 for a in gltf["accessors"] if a["type"] == "SCALAR")
    if tris != manifest["geometry"]["triangles"]:
        sys.exit("manifest says %d triangles, world.glb holds %d" % (manifest["geometry"]["triangles"], tris))
    print("daedalus-mesh-fixture 1")
    print("type 0 AIR 000000 0 1")
    for s in manifest["palette"]:
        print("type %d %s %s %d %d" % (s["ordinal"], s["type"], s["rgb"].lstrip("#"), s["translucent"], s["seeThrough"]))
    for row in json.loads(get(base + "/chunks"))["chunks"]:
        c = json.loads(get("%s/chunk/blocks?x=%d&y=%d&z=%d" % (base, row["x"], row["y"], row["z"])))
        if c["present"]:
            print("chunk %d %d %d %s" % (c["x"], c["y"], c["z"], c["data"]))
    print("triangles %d" % tris)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8088", sys.argv[2] if len(sys.argv) > 2 else "world-zero")
