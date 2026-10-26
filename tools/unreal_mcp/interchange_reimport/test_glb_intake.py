"""Offline tests for glb_intake.py: builds a tiny synthetic GLB in memory (stdlib only)."""
import json
import struct
import unittest

import glb_intake as g


def _glb(tris=1, socket_t=(0, 0.5, 0)):
    pos = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    pbin = b"".join(struct.pack("<3f", *p) for p in pos)
    idx = struct.pack("<3H", 0, 1, 2) * tris
    pad = b"\x00" * ((4 - len(idx) % 4) % 4)
    binary = pbin + idx + pad
    gl = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pbin)}, {"buffer": 0, "byteOffset": len(pbin), "byteLength": len(idx)}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}, {"bufferView": 1, "componentType": 5123, "count": 3 * tris, "type": "SCALAR"}],
        "materials": [{"name": "T_M0", "pbrMetallicRoughness": {"baseColorFactor": [1.0, 1.0, 1.0, 1]}}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}, {"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "nodes": [{"name": "SOCKET_Top", "translation": list(socket_t)}, {"name": "UCX_T", "mesh": 1}, {"name": "T", "mesh": 0, "children": [0, 1]}],
    }
    js = json.dumps(gl).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(binary), b"BIN\x00") + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


def _exp(data, tris):
    import hashlib
    return {"asset": "T", "tolerance_m": 0.001, "color_tolerance": 0.01,
            "socket": {"name": "SOCKET_Top", "gltf_translation": [0, 0.5, 0]},
            "collision": {"name": "UCX_T"},
            "materials": [{"name": "T_M0", "srgb_hex": "FFFFFF"}],
            "variants": {"A": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "tris": tris, "ucx_tris": tris, "dims_m_gltf": [1, 1, 0]}}}


class GlbIntakeTest(unittest.TestCase):
    def _run(self, data, exp, tmp="_t.glb"):
        import os, tempfile
        p = os.path.join(tempfile.mkdtemp(), tmp)
        with open(p, "wb") as fh:
            fh.write(data)
        return g.check(exp, "A", p)

    def test_pass(self):
        d = _glb()
        self.assertTrue(self._run(d, _exp(d, 1))["ok"])

    def test_wrong_tris_fails(self):
        d = _glb(tris=2)
        exp = _exp(d, 1)
        r = self._run(d, exp)
        self.assertFalse(r["ok"])
        self.assertFalse(r["checks"]["tris"])

    def test_socket_moved_fails(self):
        d = _glb(socket_t=(0, 0.6, 0))
        r = self._run(d, _exp(d, 1))
        self.assertFalse(r["checks"]["socket_translation"])

    def test_srgb_linear(self):
        lin = g.srgb_hex_to_linear("9A6B3F")
        self.assertAlmostEqual(lin[0], (0x9A / 255) ** 2.2, places=6)


if __name__ == "__main__":
    unittest.main()