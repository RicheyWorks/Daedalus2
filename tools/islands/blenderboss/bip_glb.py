# SPDX-License-Identifier: MIT
"""Minimal, dependency-light (numpy only) glTF 2.0 binary reader/writer for BIP 1 (blender-team)."""
import json, struct
import numpy as np

_CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    """-> (json dict, bin bytes). Raises ValueError on anything that is not a plain glb 2.0."""
    d = open(path, "rb").read()
    if len(d) < 20 or d[:4] != b"glTF" or struct.unpack("<I", d[4:8])[0] != 2:
        raise ValueError("not a glb 2.0: " + path)
    if struct.unpack("<I", d[8:12])[0] != len(d):
        raise ValueError("glb length field does not match file size: " + path)
    n, k = struct.unpack("<II", d[12:20])
    if k != 0x4E4F534A:
        raise ValueError("first chunk is not JSON")
    g = json.loads(d[20:20 + n])
    o = 20 + n
    binb = b""
    if o + 8 <= len(d):
        bl, bk = struct.unpack("<II", d[o:o + 8])
        if bk != 0x004E4942:
            raise ValueError("second chunk is not BIN")
        binb = d[o + 8:o + 8 + bl]
    return g, binb


def accessor(g, binb, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    dt = np.dtype(_CT[a["componentType"]]).newbyteorder("<")
    nc = _NC[a["type"]]
    if bv.get("byteStride", 0) not in (0, dt.itemsize * nc):
        raise ValueError("interleaved buffer views are not supported")
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    arr = np.frombuffer(binb, dtype=dt, count=a["count"] * nc, offset=off)
    return arr.reshape(a["count"], nc) if nc > 1 else arr


def write_glb(path_or_none, gltf, bin_chunks):
    """Pack the buffer views described by gltf (already filled in) and return the glb bytes (also written when path given)."""
    js = json.dumps(gltf, separators=(",", ":"), sort_keys=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    b = b"".join(bin_chunks)
    b += b"\0" * ((4 - len(b) % 4) % 4)
    out = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(b)) + struct.pack("<II", len(js), 0x4E4F534A) + js \
        + struct.pack("<II", len(b), 0x004E4942) + b
    if path_or_none:
        with open(path_or_none, "wb") as f:
            f.write(out)
    return out


class Builder:
    """Accumulates meshes/nodes/materials for one packet glb."""

    def __init__(self):
        self.chunks, self.bvs, self.accs, self.meshes, self.nodes, self.mats, self._mat_ix = [], [], [], [], [], [], {}
        self._len = 0

    def _view(self, arr, target):
        raw = arr.tobytes()
        pad = (4 - self._len % 4) % 4
        if pad:
            self.chunks.append(b"\0" * pad); self._len += pad
        self.bvs.append({"buffer": 0, "byteOffset": self._len, "byteLength": len(raw), "target": target})
        self.chunks.append(raw); self._len += len(raw)
        return len(self.bvs) - 1

    def _acc(self, arr, ctype, typ, target, minmax=False):
        a = {"bufferView": self._view(arr, target), "componentType": ctype, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            a["min"] = [float(x) for x in arr.min(axis=0)]; a["max"] = [float(x) for x in arr.max(axis=0)]
        self.accs.append(a)
        return len(self.accs) - 1

    def material(self, m):
        key = json.dumps(m, sort_keys=True)
        if key not in self._mat_ix:
            self._mat_ix[key] = len(self.mats); self.mats.append(m)
        return self._mat_ix[key]

    def add_mesh(self, name, prims, node=None):
        """prims: list of dict(pos (n,3) f32, nrm (n,3) f32 or None, uv (n,2) f32 or None, idx (m,) uint, mat dict). Returns node index."""
        out = []
        for p in prims:
            at = {"POSITION": self._acc(np.ascontiguousarray(p["pos"], "<f4"), 5126, "VEC3", 34962, True)}
            if p.get("nrm") is not None:
                at["NORMAL"] = self._acc(np.ascontiguousarray(p["nrm"], "<f4"), 5126, "VEC3", 34962)
            if p.get("uv") is not None:
                at["TEXCOORD_0"] = self._acc(np.ascontiguousarray(p["uv"], "<f4"), 5126, "VEC2", 34962)
            small = int(p["pos"].shape[0]) < 65536
            idx = np.ascontiguousarray(p["idx"], "<u2" if small else "<u4")
            out.append({"attributes": at, "indices": self._acc(idx, 5123 if small else 5125, "SCALAR", 34963), "material": self.material(p["mat"]), "mode": 4})
        self.meshes.append({"name": name, "primitives": out})
        n = {"name": name, "mesh": len(self.meshes) - 1}
        if node:
            n.update(node)
        self.nodes.append(n)
        return len(self.nodes) - 1

    def tri_count(self):
        return sum(self.accs[p["indices"]]["count"] // 3 for m in self.meshes for p in m["primitives"])

    def byte_size_estimate(self):
        return self._len

    def finish(self, extras):
        g = {"asset": {"version": "2.0", "generator": "blender-team bip_split 1"}, "scene": 0, "scenes": [{"nodes": list(range(len(self.nodes)))}],
             "nodes": self.nodes, "meshes": self.meshes, "materials": self.mats, "accessors": self.accs, "bufferViews": self.bvs,
             "buffers": [{"byteLength": self._len + (4 - self._len % 4) % 4}], "extras": extras}
        ext = sorted({k for m in self.mats for k in m.get("extensions", {})})
        if ext:
            g["extensionsUsed"] = ext
        return write_glb(None, g, self.chunks)
