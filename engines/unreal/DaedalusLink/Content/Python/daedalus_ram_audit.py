# SPDX-License-Identifier: MIT
"""Where the editor's RAM goes, read from the asset registry WITHOUT loading assets (ADR-064's measuring step).

    import daedalus_ram_audit; daedalus_ram_audit.run()       # writes Saved/Daedalus/ram-audit.json

The editor sat at 13.2 GB private on a 31.7 GB PC. Loading 22k assets to measure them would make it worse, so this
reads only registry tags: a texture's Dimensions and Format give its GPU/CPU size (all mips), a static mesh's
triangle and vertex counts give a rough mesh size. Totals go per owner folder (/Game/<owner>/), with the 25 biggest
assets, so each bot sees what its own island costs and what to shrink first. Read-only: it changes nothing.

The maths (no unreal import) is tested offline: test_daedalus_ram_audit.py.
"""
import json
import os
import re

# bytes per pixel for the formats the registry reports (PF_* names); block formats per 4x4 block / 16
BPP = {
    "PF_DXT1": 0.5, "PF_BC4": 0.5, "PF_ETC1": 0.5, "PF_ETC2_RGB": 0.5,
    "PF_DXT3": 1.0, "PF_DXT5": 1.0, "PF_BC5": 1.0, "PF_BC7": 1.0, "PF_BC6H": 1.0, "PF_ETC2_RGBA": 1.0,
    "PF_G8": 1.0, "PF_A8": 1.0, "PF_R8": 1.0,
    "PF_G16": 2.0, "PF_R16F": 2.0, "PF_V8U8": 2.0,
    "PF_B8G8R8A8": 4.0, "PF_R8G8B8A8": 4.0, "PF_FloatRGB": 4.0, "PF_A2B10G10R10": 4.0, "PF_R32_FLOAT": 4.0,
    "PF_FloatRGBA": 8.0, "PF_A16B16G16R16": 8.0, "PF_R16G16B16A16_UNORM": 8.0,
    "PF_A32B32G32R32F": 16.0,
}
DEFAULT_BPP = 4.0           # unknown format: assume uncompressed RGBA8, the safe (high) side
MIP_FACTOR = 4.0 / 3.0      # a full mip chain adds a third
MESH_BYTES_PER_VERTEX = 32  # position + normal/tangent + one UV, packed; LODs and collision not counted
_DIMS = re.compile(r"^\s*(\d+)\s*x\s*(\d+)(?:\s*x\s*(\d+))?\s*$")


# When the registry gives no PF_* pixel format, the compression setting says what the cook makes of it.
BY_COMPRESSION = {
    "TC_Normalmap": "PF_BC5", "TC_Grayscale": "PF_G8", "TC_Displacementmap": "PF_G8", "TC_Alpha": "PF_BC4",
    "TC_HDR": "PF_FloatRGBA", "TC_HDR_Compressed": "PF_BC6H", "TC_BC7": "PF_BC7", "TC_VectorDisplacementmap": "PF_B8G8R8A8",
    "TC_EditorIcon": "PF_B8G8R8A8", "TC_DistanceFieldFont": "PF_G8", "TC_Masks": "PF_DXT1",
}


def pixel_format(fmt, compression=None, has_alpha=None):
    """A PF_* name: the tag itself when it is one, else from the compression setting (TC_Default: DXT5 with alpha,
    DXT1 without), else None (unknown, counted at RGBA8)."""
    f = str(fmt or "").strip()
    if f.startswith("PF_"):
        return f
    c = str(compression or "").strip()
    if c in BY_COMPRESSION:
        return BY_COMPRESSION[c]
    if c in ("TC_Default", "") and has_alpha is not None:
        return "PF_DXT5" if str(has_alpha).strip().lower() in ("true", "1") else "PF_DXT1"
    return None


def texture_bytes(dims, fmt, mips=True):
    """Estimated resident bytes of a texture from its registry tags, or 0 if the dimensions don't parse."""
    m = _DIMS.match(str(dims or ""))
    if not m:
        return 0
    w, h, d = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
    b = w * h * d * BPP.get(str(fmt or "").strip(), DEFAULT_BPP)
    return int(b * (MIP_FACTOR if mips else 1.0))


def mesh_bytes(vertices, triangles):
    try:
        v, t = int(vertices or 0), int(triangles or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, v) * MESH_BYTES_PER_VERTEX + max(0, t) * 3 * 4


def owner(package, depth=1):
    """The owner folder of a package: /Game/<owner>/ (depth 1) or /Game/<owner>/<sub>/ (depth 2)."""
    parts = [p for p in str(package).split("/") if p]
    if len(parts) < 2 or parts[0] != "Game":
        return "/" + parts[0] + "/" if parts else "/"
    keep = parts[1:1 + depth] if len(parts) > depth + 1 else parts[1:-1]
    return "/Game/" + "".join(p + "/" for p in keep)


def summarize(rows, top=25, depth=1):
    """rows: dicts with package, kind ('texture'|'mesh'), bytes. Totals per owner (largest first) and the top assets."""
    owners = {}
    for r in rows:
        o = owners.setdefault(owner(r["package"], depth), {"owner": owner(r["package"], depth), "bytes": 0,
                                                            "texture_bytes": 0, "mesh_bytes": 0, "assets": 0})
        o["bytes"] += r["bytes"]
        o[r["kind"] + "_bytes"] += r["bytes"]
        o["assets"] += 1
    by_owner = sorted(owners.values(), key=lambda o: (-o["bytes"], o["owner"]))
    biggest = sorted(rows, key=lambda r: (-r["bytes"], r["package"]))[:top]
    total = sum(r["bytes"] for r in rows)
    return {"total_bytes": total, "total_mb": round(total / 2 ** 20, 1), "assets": len(rows),
            "owners": by_owner, "biggest": biggest}


def _tag(asset_data, name):
    try:
        v = asset_data.get_tag_value(name)
        return None if v is None else str(v)
    except Exception:   # older builds name it differently; a missing tag only means "unknown"
        return None


def _rows():
    import unreal   # only inside the editor
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    rows, unknown = [], {"format": 0, "texture": 0, "mesh": 0}   # what the tags couldn't tell us, reported honestly
    for cls, kind in (("Texture2D", "texture"), ("StaticMesh", "mesh")):
        flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", cls)],
                              package_paths=["/Game"], recursive_paths=True)
        for a in ar.get_assets(flt):
            pkg = str(a.package_name)
            if kind == "texture":
                pf = pixel_format(_tag(a, "Format"), _tag(a, "CompressionSettings"), _tag(a, "HasAlphaChannel"))
                b = texture_bytes(_tag(a, "Dimensions"), pf)
                if pf is None:
                    unknown["format"] += 1
            else:
                b = mesh_bytes(_tag(a, "Vertices"), _tag(a, "Triangles"))
            if b == 0:
                unknown[kind] += 1
            rows.append({"package": pkg, "kind": kind, "bytes": b})
    return rows, unknown


def run(top=25, depth=1):
    import unreal
    rows, unknown = _rows()
    report = summarize(rows, top=top, depth=depth)
    report["unknown"] = unknown
    out = os.path.join(unreal.Paths.project_saved_dir(), "Daedalus", "ram-audit.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    report["path"] = out
    # keep the bridge reply small: the file has everything
    return {"path": out, "total_mb": report["total_mb"], "assets": report["assets"], "unknown": unknown,
            "owners": [{"owner": o["owner"], "mb": round(o["bytes"] / 2 ** 20, 1)} for o in report["owners"][:12]]}
