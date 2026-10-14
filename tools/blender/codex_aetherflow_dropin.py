# SPDX-License-Identifier: MIT
"""Retain Sol's three reviewed Aetherflow plants as common-origin FBX meshes.

Run only in an explicitly factory-started background Blender process::

    blender --background --factory-startup --python tools/blender/codex_aetherflow_dropin.py -- --output C:/retained/new-folder

This repacks existing geometry; it does not generate plants, render, contact
Unreal or claim native delivery. Original waterline origins and metre scale stay
intact, including glasskelp's intentionally submerged geometry.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time


DEFAULT_SOURCE = Path("C:/Users/730ri/projects/Daedalus2/artifacts/waterways/aetherflow-v2")
SOURCE_COMMIT = "44f0b1583162aeeebd6f4784b539022c0760c193"
SEED = 617024
PLANTS = {
    "ribbon_reeds": {"bytes": 62472, "sha256": "3124f31b2889f9610b79cdd582a03fdc40a13fc919ebcfb70d2065a966fa0695", "meshes": 44, "triangles": 2152},
    "star_lilies": {"bytes": 62204, "sha256": "0cfa8be1dc9fc71f9efce89601b3d7e6a4286735bea55532f4fec24c23ffa209", "meshes": 46, "triangles": 1940},
    "glasskelp": {"bytes": 91780, "sha256": "97b6af850c377fb6b76b1499b6ceecd1091cd9244f03f7141242c4699ea6bf86", "meshes": 72, "triangles": 3072},
}
WITNESSES = {
    "Delivery_Receipt.json": (12741, "13ca2e81f94a28228ee430146ddd54dd70bae9797c9f584b28024c5ad15ba142"),
    "../Aetherflow_Package_Receipt.json": (9940, "47da61d38deccaf8ed84e1f077d11b131b6730426372b7e7629cd0a8672390c4"),
    "Aetherflow_Aquatic_Life.png": (1670458, "1400c668cb065316a58ac7c91f9a5249297f3104802483c6f800654b1128551c"),
    "Aetherflow_Nursery_detail.png": (1907798, "437ad2d53b6932bc4ed6ff42d75ee4bd51bb4e6f33fd7fdb49a1b776fec2c052"),
    "Aetherflow_Reach_day.png": (2022426, "c29db29874d275b4b717665fe8fc13164cbb3f3d2d8779eff9774e1f266f4d8d"),
    "Aetherflow_Reach_dusk.png": (1955744, "c93623e93a9eca107bfcfbe75a1b28f6f84e302edc7c012f4ddc5f18d865d1dc"),
    "Aetherflow_Willowdrift_player.png": (1568013, "b535bf1366c795a5534cf740b019fa213808d0b5cc4e882e3e1ad82f95aba411"),
}
# Same selected FBX basis/scale options as codex_contest_island.build().
FBX_OPTIONS = {
    "use_selection": True, "use_mesh_modifiers": True,
    "apply_scale_options": "FBX_SCALE_ALL", "axis_forward": "-Y",
    "axis_up": "Z", "bake_anim": False,
    "global_scale": 1.0, "apply_unit_scale": True,
    "object_types": {"MESH"}, "use_custom_props": True,
}
POSITION_TOLERANCE_M = 0.000002
NORMAL_TOLERANCE = 0.00002


class PreservationError(ValueError):
    def __init__(self, message, diagnostics):
        self.diagnostics = diagnostics
        super().__init__(message + ": " + json.dumps(diagnostics["measurements"], sort_keys=True))


def _write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def _pin_sources(source):
    expected = dict(WITNESSES)
    for kind, spec in PLANTS.items():
        expected["modules/Life_" + kind + ".glb"] = (spec["bytes"], spec["sha256"])
    actual = {}
    for relative, (size, digest) in expected.items():
        witness = _fingerprint(source / relative)
        if (witness["bytes"], witness["sha256"]) != (size, digest):
            raise ValueError("source witness changed: " + relative)
        actual[relative] = witness
    return actual


def _gltf_contract(path, kind):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<III", data)
    length, chunk = struct.unpack_from("<II", data, 12)
    if (magic, version, total, chunk) != (0x46546C67, 2, len(data), 0x4E4F534A):
        raise ValueError("unexpected GLB header")
    gltf = json.loads(data[20:20 + length].decode("utf-8").rstrip(" \x00"))
    if any(gltf.get(key) for key in ("animations", "skins", "images", "textures")):
        raise ValueError("only the exact static self-contained plant modules are supported")
    if gltf.get("extensionsRequired") or any(b.get("uri") for b in gltf.get("buffers", [])):
        raise ValueError("unexpected external buffer or required GLB extension")
    nodes = gltf["nodes"]
    if any(any(key in node for key in ("translation", "rotation", "scale", "matrix")) for node in nodes):
        raise ValueError("pinned plant GLB must retain identity node transforms")
    roots = [node for node in nodes if node.get("name") == "SW_" + kind + "_Root"]
    if len(roots) != 1 or len(gltf["meshes"]) != PLANTS[kind]["meshes"]:
        raise ValueError("unexpected source root or mesh count")
    extras = roots[0].get("extras", {})
    if (extras.get("asset_kind"), extras.get("seed"), extras.get("units"),
        extras.get("forward_axis"), extras.get("up_axis"), extras.get("waterline_local_z")) != (
            kind, SEED, "metres", "+X", "+Z", 0.0):
        raise ValueError("source root provenance/basis changed")
    materials = gltf["materials"]
    counts = Counter()
    minimum = [math.inf] * 3
    maximum = [-math.inf] * 3
    for mesh in gltf["meshes"]:
        if len(mesh["primitives"]) != 1:
            raise ValueError("unexpected source primitive splitting")
        primitive = mesh["primitives"][0]
        if primitive.get("mode", 4) != 4 or set(primitive["attributes"]) != {"POSITION", "NORMAL"}:
            raise ValueError("unexpected source geometry attributes or topology")
        position = gltf["accessors"][primitive["attributes"]["POSITION"]]
        for axis in range(3):
            minimum[axis] = min(minimum[axis], position["min"][axis])
            maximum[axis] = max(maximum[axis], position["max"][axis])
        count = gltf["accessors"][primitive["indices"]]["count"]
        if count % 3:
            raise ValueError("non-triangular source index count")
        counts[materials[primitive["material"]]["name"]] += count // 3
    if sum(counts.values()) != PLANTS[kind]["triangles"]:
        raise ValueError("source triangle count changed")
    for material in materials:
        pbr = material["pbrMetallicRoughness"]
        if (not material["name"].startswith("SW_Life_") or
            material.get("alphaMode", "OPAQUE") != "OPAQUE" or
            pbr["baseColorFactor"][3] != 1 or not material.get("doubleSided") or
            material.get("extensions", {}).get("KHR_materials_clearcoat", {}).get("clearcoatFactor") != .25):
            raise ValueError("source material contract changed")
    return {"asset": gltf["asset"], "root_name": roots[0]["name"],
            "root_extras": extras, "mesh_count": len(gltf["meshes"]),
            "triangles": sum(counts.values()), "material_triangle_counts": dict(counts),
            "bounds_gltf_y_up_metres": {"min": minimum, "max": maximum},
            "bounds_blender_z_up_metres": {
                "min": [minimum[0], -maximum[2], minimum[1]],
                "max": [maximum[0], -minimum[2], maximum[1]]},
            "materials_linear_gltf": materials,
            "extensions_used": gltf.get("extensionsUsed", []),
            "extensions_required": gltf.get("extensionsRequired", []),
            "images": 0, "textures": 0, "animations": 0, "skins": 0,
            "nodes": [{"name": node.get("name"), "extras": node.get("extras", {})} for node in nodes]}


def _matrix_rows(matrix):
    return [[float(value) for value in row] for row in matrix]


def _payload(bpy, objects, root_matrix, material_names):
    """Read evaluated geometry in the unchanged source-root coordinate system."""
    vertices, faces, normals, material_indices, smooth = [], [], [], [], []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    transforms, triangles, custom_normal_meshes = [], 0, 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            transform = root_matrix.inverted() @ evaluated.matrix_world
            custom_normal_meshes += int(mesh.has_custom_normals)
            normal_matrix = transform.to_3x3().inverted().transposed()
            transforms.append({"object": obj.name, "object_to_source_root": _matrix_rows(transform),
                               "source_root_to_object": _matrix_rows(transform.inverted())})
            offset = len(vertices)
            vertices.extend(tuple(float(v) for v in (transform @ vertex.co)) for vertex in mesh.vertices)
            if hasattr(mesh, "calc_normals_split"):
                mesh.calc_normals_split()
            for polygon in mesh.polygons:
                material = mesh.materials[polygon.material_index]
                if material is None or material.name not in material_names:
                    raise ValueError("missing or renamed imported material")
                faces.append(tuple(offset + index for index in polygon.vertices))
                material_indices.append(material_names.index(material.name))
                smooth.append(bool(polygon.use_smooth))
                for index in polygon.loop_indices:
                    source_normal = (mesh.corner_normals[index].vector if hasattr(mesh, "corner_normals")
                                     else mesh.loops[index].normal)
                    normal = (normal_matrix @ source_normal).normalized()
                    normals.append(tuple(float(v) for v in normal))
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
        finally:
            evaluated.to_mesh_clear()
    if not vertices or not faces or not all(math.isfinite(v) for point in vertices for v in point):
        raise ValueError("empty or invalid imported geometry")
    minimum = [min(point[axis] for point in vertices) for axis in range(3)]
    maximum = [max(point[axis] for point in vertices) for axis in range(3)]
    counts = Counter(material_names[index] for index in material_indices)
    report = {"evaluated_mesh_objects": len(objects), "vertices": len(vertices),
              "polygons": len(faces), "triangles": triangles,
              "bounds_metres": {"min": minimum, "max": maximum},
              "dimensions_metres": [maximum[i] - minimum[i] for i in range(3)],
              "material_slots": material_names, "material_face_counts": dict(counts),
              "custom_corner_normals": len(normals), "meshes_with_custom_normals": custom_normal_meshes,
              "part_transforms": transforms}
    return {"vertices": vertices, "faces": faces, "normals": normals,
            "material_indices": material_indices, "smooth": smooth, "report": report}


def _surface_corners(payload):
    """Match oriented faces by exact geometry/material, independent of join order.

    Cyclic corner rotations are harmless; reversed winding is a different face.
    No coordinate quantization is used, so this cannot mask vertex movement.
    """
    surfaces = {}
    cursor = 0
    for face, material, smooth in zip(payload["faces"], payload["material_indices"], payload["smooth"]):
        points = tuple(payload["vertices"][index] for index in face)
        normals = tuple(payload["normals"][cursor:cursor + len(face)])
        cursor += len(face)
        start = min(range(len(face)), key=lambda index: points[index:] + points[:index])
        key = (material, smooth, points[start:] + points[:start])
        surfaces.setdefault(key, []).append(normals[start:] + normals[:start])
    return {key: sorted(values) for key, values in surfaces.items()}


def _compare(before, after):
    failures = []
    same_vertices = len(before["vertices"]) == len(after["vertices"])
    position_error = (max(abs(a - b) for x, y in zip(sorted(before["vertices"]), sorted(after["vertices"]))
                          for a, b in zip(x, y)) if same_vertices else None)
    left, right = _surface_corners(before), _surface_corners(after)
    aligned = left.keys() == right.keys() and all(len(left[key]) == len(right[key]) for key in left)
    normal_error, angular_error = None, None
    if aligned:
        normal_error = angular_error = 0.0
        for key in left:
            for old_face, new_face in zip(left[key], right[key]):
                for old, new in zip(old_face, new_face):
                    normal_error = max(normal_error, *(abs(a - b) for a, b in zip(old, new)))
                    cross = (old[1] * new[2] - old[2] * new[1],
                             old[2] * new[0] - old[0] * new[2],
                             old[0] * new[1] - old[1] * new[0])
                    dot = sum(a * b for a, b in zip(old, new))
                    angle = math.degrees(math.atan2(math.sqrt(sum(v * v for v in cross)), dot))
                    angular_error = max(angular_error, angle)
    else:
        failures.append("exact oriented face geometry/material/smooth assignments changed")
    if position_error is None or position_error > POSITION_TOLERANCE_M:
        failures.append("vertex count or position tolerance")
    if normal_error is not None and normal_error > NORMAL_TOLERANCE:
        failures.append("corner normal tolerance")
    for key in ("triangles", "vertices", "polygons", "material_slots", "material_face_counts", "custom_corner_normals"):
        if before["report"][key] != after["report"][key]:
            failures.append("evaluated " + key)
    measurements = {"maximum_position_error_metres": position_error,
                    "position_tolerance_metres": POSITION_TOLERANCE_M,
                    "exact_oriented_faces_aligned": aligned,
                    "maximum_corner_normal_component_error": normal_error,
                    "maximum_corner_normal_angular_error_degrees": angular_error,
                    "normal_tolerance": NORMAL_TOLERANCE}
    if failures:
        raise PreservationError("merge preservation rejected: " + "; ".join(failures),
                                {"measurements": measurements,
                                 "before_merge": before["report"], "after_merge": after["report"]})
    return dict(measurements, geometry_and_materials_preserved=True,
                merge_method="Blender object.join retaining imported mesh custom data")


def _convert(bpy, source, output, kind, witnesses):
    from mathutils import Matrix

    started = time.perf_counter()
    path = source / "modules" / ("Life_" + kind + ".glb")
    contract = _gltf_contract(path, kind)
    # Factory-only background process: remove the preceding import and its
    # datablocks before loading one module, avoiding renamed shared materials.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    if abs(bpy.context.scene.unit_settings.scale_length - 1.0) > 1e-9:
        raise ValueError("unexpected Blender metre unit scale")
    roots = [obj for obj in bpy.context.scene.objects if obj.name == contract["root_name"]]
    if len(roots) != 1:
        raise ValueError("Blender did not retain the exact source root")
    root = roots[0]
    if any(abs(root.matrix_world[i][j] - (1.0 if i == j else 0.0)) > 1e-7
           for i in range(4) for j in range(4)):
        raise ValueError("unexpected root transform; refuse to move or scale the source waterline")
    if any(root.get(key) != value for key, value in contract["root_extras"].items()):
        raise ValueError("Blender did not retain source root extras")
    objects = sorted((obj for obj in root.children_recursive if obj.type == "MESH"), key=lambda obj: obj.name)
    all_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(objects) != PLANTS[kind]["meshes"] or set(objects) != set(all_meshes):
        raise ValueError("unexpected imported scene objects")
    names = [material["name"] for material in contract["materials_linear_gltf"]]
    materials = [bpy.data.materials.get(name) for name in names]
    if any(material is None for material in materials):
        raise ValueError("source material names were not retained")
    before = _payload(bpy, objects, root.matrix_world.copy(), names)
    for edge in ("min", "max"):
        if any(abs(a - b) > POSITION_TOLERANCE_M for a, b in zip(
                before["report"]["bounds_metres"][edge],
                contract["bounds_blender_z_up_metres"][edge])):
            raise ValueError("GLB importer changed source basis, scale or bounds")
    if before["report"]["triangles"] != contract["triangles"]:
        raise ValueError("GLB importer changed evaluated triangle count")
    if before["report"]["material_face_counts"] != contract["material_triangle_counts"]:
        raise ValueError("GLB importer changed source material face counts")
    name = "CodexAetherflow_" + kind + "_" + str(SEED)
    # Pinned plant nodes are already identity in original root coordinates.
    # R1 rebuilt topology and called normals_split_custom_set a second time.
    # Joining imported custom data avoids that extra normal-encoding step.
    for item in objects:
        if any(abs(item.matrix_world[i][j] - (1.0 if i == j else 0.0)) > 1e-7
               for i in range(4) for j in range(4)):
            raise ValueError("unexpected part transform; refuse to re-encode its normals")
    for item in bpy.context.view_layer.objects:
        item.select_set(item in objects)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    obj.name = name
    mesh = obj.data
    mesh.name = name
    # Keep the exact GLB slot order while retaining imported material datablocks.
    face_materials = [mesh.materials[polygon.material_index].name for polygon in mesh.polygons]
    mesh.materials.clear()
    for material in materials:
        mesh.materials.append(material)
    for polygon, material_name in zip(mesh.polygons, face_materials):
        polygon.material_index = names.index(material_name)
    for key, value in contract["root_extras"].items():
        obj[key] = value
    obj["source_author"] = "SolUltra"
    obj["source_owner_handle"] = "buckwild-sol"
    obj["source_root_name"] = root.name
    obj["source_glb_sha256"] = PLANTS[kind]["sha256"]
    obj["conversion_only"] = True
    bpy.context.view_layer.update()
    after = _payload(bpy, [obj], Matrix.Identity(4), names)
    preservation = _compare(before, after)
    for item in bpy.context.view_layer.objects:
        item.select_set(item == obj)
    bpy.context.view_layer.objects.active = obj
    fbx = output / (name + ".fbx")
    if fbx.exists():
        raise FileExistsError(str(fbx))
    export_started = time.perf_counter()
    bpy.ops.export_scene.fbx(filepath=str(fbx), **FBX_OPTIONS)
    export_seconds = time.perf_counter() - export_started
    if not fbx.is_file() or fbx.stat().st_size == 0:
        raise ValueError("FBX exporter did not produce a nonempty payload")
    if _pin_sources(source) != witnesses:
        raise ValueError("original sources changed during conversion")
    report = {
        "schema": "daedalus.codex-aetherflow-dropin.v1", "converter_revision": 2, "name": name,
        "kind": "retained_source_conversion", "plant": kind, "seed": SEED,
        "stage": "retained_fbx_exported", "native_imported": False,
        "native_saved": False, "new_geometry_generated": False,
        "source_author": "SolUltra", "source_owner_handle": "buckwild-sol",
        "source_commit": SOURCE_COMMIT, "source_witnesses": witnesses,
        "review_provenance": {"owner_messages": [30951, 30952],
                              "owner_personally_inspected_views": 5,
                              "read_only_helper_inspected": "Aetherflow_Aquatic_Life.png",
                              "native_visual_acceptance": False},
        "source_gltf_contract": contract, "source_root_extras": contract["root_extras"],
        "coordinates": {
            "geometry_units": "metres", "blender_forward": "+X", "blender_up": "+Z",
            "source_waterline_local_z": 0.0, "recentered": False, "rescaled": False,
            "gltf_y_up_to_blender_z_up": [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
            "blender_z_up_to_gltf_y_up": [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]],
            "merged_object_matrix": _matrix_rows(obj.matrix_world),
            "scene_unit_scale_length": float(bpy.context.scene.unit_settings.scale_length),
            "fbx_options": {key: sorted(value) if isinstance(value, set) else value
                            for key, value in FBX_OPTIONS.items()},
            "glasskelp_below_waterline_is_intentional": kind == "glasskelp"},
        "before_merge": before["report"], "after_merge": after["report"],
        "preservation": preservation, "original_payloads_unchanged": True,
        "blender_version": bpy.app.version_string,
        "elapsed_s": {"conversion_and_export": round(time.perf_counter() - started, 6),
                      "fbx_export": round(export_seconds, 6)},
        "artifacts": {"fbx": {"path": str(fbx), "fingerprint": _fingerprint(fbx)}},
        "limits": ["FBX reimport and Unreal effective material/scale acceptance remain unmeasured.",
                   "No collision hulls, native water, ecology, navigation or gameplay were added.",
                   "FBX material translation may omit clearcoat/two-sided behavior; exact GLB factors are retained for native mapping.",
                   "No tests, render or native operation was performed by this converter."],
    }
    receipt = output / (name + ".receipt.json")
    _write_new(receipt, report)
    print(json.dumps({"name": name, "stage": report["stage"],
                      "receipt": str(receipt), "dimensions_metres": after["report"]["dimensions_metres"],
                      "triangles": after["report"]["triangles"], "material_slots": names,
                      "fbx": report["artifacts"]["fbx"]}, sort_keys=True), flush=True)
    return {"name": name, "receipt": _fingerprint(receipt), "fbx": _fingerprint(fbx),
            "dimensions_metres": after["report"]["dimensions_metres"],
            "triangles": after["report"]["triangles"], "material_slots": names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True, help="Fresh retained directory; parent must already exist")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    import bpy

    if not bpy.app.background or "--factory-startup" not in sys.argv:
        raise RuntimeError("use a dedicated --background --factory-startup Blender process")
    source = args.source_root.resolve(strict=True)
    output = args.output.resolve()
    if output == source or source in output.parents:
        raise ValueError("retained output must be outside Sol's original source directory")
    if output.exists() or not output.parent.is_dir():
        raise FileExistsError("output must be new and its parent must exist: " + str(output))
    witnesses = _pin_sources(source)
    delivery = json.loads((source / "Delivery_Receipt.json").read_text(encoding="utf-8"))
    package = json.loads((source.parent / "Aetherflow_Package_Receipt.json").read_text(encoding="utf-8"))
    if (delivery.get("stage") != "BLENDER_AUTHORED_AND_EXPORTED" or
        delivery.get("nativeImported") is not False or package.get("sourceCommit") != SOURCE_COMMIT):
        raise ValueError("unexpected Sol delivery stage or source commit")
    output.mkdir()
    results = []
    try:
        for kind in PLANTS:
            results.append(_convert(bpy, source, output, kind, witnesses))
        unchanged = _pin_sources(source) == witnesses
        if not unchanged:
            raise ValueError("original sources changed before batch completion")
        batch = {"schema": "daedalus.codex-aetherflow-dropin-batch.v1",
                 "stage": "three_retained_fbx_exported", "source_author": "SolUltra",
                 "source_owner_handle": "buckwild-sol", "source_commit": SOURCE_COMMIT,
                 "seed": SEED, "source_witnesses": witnesses, "artifacts": results,
                 "original_payloads_unchanged": unchanged, "native_imported": False,
                 "native_saved": False, "tests_run": False, "renders_run": False,
                 "converter_source": _fingerprint(Path(__file__))}
        _write_new(output / "Aetherflow_Dropin_Receipt.json", batch)
        print(json.dumps(batch, sort_keys=True), flush=True)
    except Exception as error:
        try:
            unchanged = _pin_sources(source) == witnesses
        except Exception:
            unchanged = False
        _write_new(output / "FAILED.json", {"stage": "conversion_failed", "converter_revision": 2,
                                           "error": str(error), "diagnostics": getattr(error, "diagnostics", None),
                                           "completed": results, "original_payloads_unchanged": unchanged})
        raise


if __name__ == "__main__":
    main()
