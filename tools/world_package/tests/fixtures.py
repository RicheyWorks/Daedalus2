# SPDX-License-Identifier: MIT
"""Small synthetic World Package v1 fixtures; never copied from live campaigns."""

import copy
import json
import struct
import zipfile

MANIFEST = {"format": "daedalus-world-package", "version": 1,
            "world": {"id": "world-zero", "revision": 12, "title": "Fixture", "style": "blocks"},
            "geometry": {"file": "world.glb", "chunks": 1, "triangles": 12}, "assets": []}


def glb(gltf=None):
    payload = json.dumps(gltf if gltf is not None else {"asset": {"version": "2.0"}, "nodes": [{}]}).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<IIIII", 0x46546C67, 2, 20 + len(payload), len(payload), 0x4E4F534A) + payload


def package(path, manifest=None, glb_data=None, extra=()):
    value = copy.deepcopy(MANIFEST if manifest is None else manifest)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(value))
        archive.writestr("world.glb", glb() if glb_data is None else glb_data)
        for name, data in extra:
            archive.writestr(name, data)
    return path


def receipt(plan):
    return {"format": "daedalus-world-import-receipt", "version": 1, "status": "accepted",
            "world_id": plan["world"]["id"], "revision": plan["world"]["revision"],
            "package_sha256": plan["source"]["package_sha256"],
            "destination_root": plan["destination"]["root"],
            "acceptance_reference": "synthetic-owner-test-evidence"}
