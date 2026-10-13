# SPDX-License-Identifier: MIT
"""Pure quest-flag derivation for pyth_quest_ue.py: (mesh_name, tags) pairs -> counts keyed by mesh base name and tag."""
def flags_from_actors(pairs, base=None):
    f = dict(base or {})
    for mesh, tags in pairs:
        if mesh:
            b = mesh.rsplit("_V", 1)[0] if "_V" in mesh else mesh
            f[b] = f.get(b, 0) + 1
        for t in tags: f[t] = f.get(t, 0) + 1
    return f
