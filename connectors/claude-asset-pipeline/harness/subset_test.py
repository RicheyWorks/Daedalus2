# SPDX-License-Identifier: MIT
"""Portable exact-subset admission checks using real, small GLB BIN fixtures.

Run ``python harness/subset_test.py`` after the module is ready. No editor,
connector, exporter, saved project, network or production asset is used. The
fixtures are synthetic file witnesses, not evidence of playable/native work.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))
from asset_pipeline import subset  # noqa: E402


NAMES = ("A", "B", "C", "D")
SELECTED = NAMES[:3]


def fingerprint(path):
    """Independent pin construction; does not reuse the code under test."""
    raw = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def pack_glb(document, binary):
    document = copy.deepcopy(document)
    document["buffers"] = [{"byteLength": len(binary)}]
    js = json.dumps(document, separators=(",", ":"), allow_nan=False).encode()
    js += b" " * (-len(js) % 4)
    padded = bytes(binary) + b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(padded)
    return (struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<I4s", len(js), b"JSON") + js
            + struct.pack("<I4s", len(padded), b"BIN\0") + padded)


def fixture(names=NAMES, *, indexed=True, interleaved=False, aliases=None,
            mesh_order=None, material_order=None, reorder_vertices=False,
            cycle=0, reverse_winding=False, reorder_triangles=False,
            change=None):
    """Real indexed/nonindexed triangles, normals and UVs; every node is a root.

    The interior vertex can move while counts and bounding boxes stay equal.
    Interleaving uses a 36-byte stride, including four unused padding bytes.
    """
    aliases = aliases or {}
    geometry_names = list(dict.fromkeys(aliases.get(n, n) for n in names))
    mesh_order = list(mesh_order or geometry_names)
    material_order = list(material_order or geometry_names)
    if set(mesh_order) != set(geometry_names) or set(material_order) != set(geometry_names):
        raise ValueError("Fixture orders must name the exact geometry set")
    binary = bytearray()
    doc = {"asset": {"version": "2.0", "generator": "subset portable fixture"},
           "scene": 0, "scenes": [{"nodes": list(range(len(names)))}],
           "nodes": [], "meshes": [], "materials": [], "accessors": [],
           "bufferViews": []}

    def view(payload, **extra):
        binary.extend(b"\0" * (-len(binary) % 4))
        result = len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer": 0, "byteOffset": len(binary),
                                   "byteLength": len(payload), **extra})
        binary.extend(payload)
        return result

    def accessor(view_index, count, kind, component=5126, **extra):
        result = len(doc["accessors"])
        doc["accessors"].append({"bufferView": view_index, "componentType": component,
                                 "count": count, "type": kind, **extra})
        return result

    for name in material_order:
        value = NAMES.index(name)
        doc["materials"].append({
            "name": "Mat_" + name, "doubleSided": True,
            "pbrMetallicRoughness": {"baseColorFactor": [.2 + value * .1, .4, .6, 1],
                                     "metallicFactor": .3, "roughnessFactor": .7},
            "emissiveFactor": [.1, .2, .3] if name == "C" else [0, 0, 0]})

    for name in mesh_order:
        positions = [[-1., 0., 0.], [1., 0., 0.], [1., 1., 0.],
                     [-1., 1., 0.], [0., .4, 0.]]
        normals = [[0., 0., 1.] for _ in positions]
        uvs = [[(p[0] + 1) / 2, p[1]] for p in positions]
        if name == "A" and change == "position":
            positions[4][1] = .45
        if name == "A" and change == "normal":
            normals[4] = [0., .6, .8]
        if name == "A" and change == "uv":
            uvs[4][0] = .55
        triangles = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
        if reorder_triangles:
            triangles = [triangles[i] for i in (3, 1, 0, 2)]
        if reverse_winding:
            triangles = [(a, c, b) for a, b, c in triangles]
        triangles = [t[cycle:] + t[:cycle] for t in triangles]
        if reorder_vertices:
            order = [4, 2, 0, 3, 1]
            inverse = {old: new for new, old in enumerate(order)}
            positions = [positions[i] for i in order]
            normals = [normals[i] for i in order]
            uvs = [uvs[i] for i in order]
            triangles = [tuple(inverse[i] for i in tri) for tri in triangles]
        indices = [index for tri in triangles for index in tri]
        if not indexed:
            positions, normals, uvs = ([values[i] for i in indices]
                                       for values in (positions, normals, uvs))
        count = len(positions)
        low = [min(p[i] for p in positions) for i in range(3)]
        high = [max(p[i] for p in positions) for i in range(3)]
        if interleaved:
            data = b"".join(struct.pack("<8fI", *(p + n + uv), 0x6A6A6A6A)
                            for p, n, uv in zip(positions, normals, uvs))
            v = view(data, byteStride=36, target=34962)
            attributes = {"POSITION": accessor(v, count, "VEC3", byteOffset=0,
                                                min=low, max=high),
                          "NORMAL": accessor(v, count, "VEC3", byteOffset=12),
                          "TEXCOORD_0": accessor(v, count, "VEC2", byteOffset=24)}
        else:
            attributes = {}
            for semantic, values, kind in (("POSITION", positions, "VEC3"),
                                            ("NORMAL", normals, "VEC3"),
                                            ("TEXCOORD_0", uvs, "VEC2")):
                width = len(values[0])
                data = b"".join(struct.pack("<" + "f" * width, *p) for p in values)
                v = view(data, target=34962)
                bounds = {"min": low, "max": high} if semantic == "POSITION" else {}
                attributes[semantic] = accessor(v, count, kind, **bounds)
        primitive = {"attributes": attributes, "material": material_order.index(name), "mode": 4}
        if indexed:
            v = view(struct.pack("<" + "H" * len(indices), *indices), target=34963)
            primitive["indices"] = accessor(v, len(indices), "SCALAR", component=5123)
        doc["meshes"].append({"name": "GenericMesh_" + name, "primitives": [primitive]})

    for name in names:
        node = {"name": name, "mesh": mesh_order.index(aliases.get(name, name)),
                "extras": {"module_role": "route" if name == "A" else "heartstone", "seed": 842401}}
        if name != "A":
            value = NAMES.index(name)
            node.update(translation=[value * 2., 0., value * .25],
                        rotation=[0., 0., math.sin(.1), math.cos(.1)], scale=[1., 1., 1.])
        doc["nodes"].append(node)
    return doc, binary


class SubsetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="static-subset-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.serial = 0
        self.source = self.write(*fixture())
        self.plan = subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def write(self, document, binary):
        self.serial += 1
        path = self.directory / ("fixture-%02d.glb" % self.serial)
        with path.open("xb") as destination:
            destination.write(pack_glb(document, binary))
        return path

    def admit(self, document=None, binary=None, plan=None, **options):
        if document is None:
            document, binary = fixture(SELECTED, **options)
        path = self.write(document, binary)
        return subset.admit(self.plan if plan is None else plan, str(path), fingerprint(path))

    def reject_document(self, document, binary):
        with self.assertRaises(ValueError):
            self.admit(document, binary)

    def cli(self, arguments):
        env = dict(os.environ, PYTHONPATH=str(PIPELINE), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", "-m", "asset_pipeline.subset", *arguments],
                              cwd=PIPELINE, env=env, capture_output=True, text=True,
                              timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def plan_arguments(self):
        pin = fingerprint(self.source)
        return ["plan", "--source", str(self.source), "--sha256", pin["sha256"],
                "--bytes", str(pin["bytes"]), "--nodes", *SELECTED]

    def test_plan_is_pinned_json_contract(self):
        self.assertEqual(self.plan["schema"], "daedalus.static-subset.v1")
        self.assertEqual(self.plan["nodes"], list(SELECTED))
        self.assertEqual({k: self.plan["source"][k] for k in ("sha256", "bytes")}, fingerprint(self.source))
        self.assertEqual(Path(self.plan["source"]["path"]).resolve(), self.source.resolve())
        self.assertEqual(json.loads(json.dumps(self.plan)), self.plan)

    def test_exact_subset_passes_without_native_readiness(self):
        report = self.admit()
        self.assertIs(report["admitted"], True)
        self.assertIs(report["native_ready"], False)

    def test_one_two_and_three_nodes_are_supported(self):
        for count in (1, 2, 3):
            with self.subTest(nodes=count):
                names = list(SELECTED[:count])
                plan = subset.make_plan(str(self.source), names, fingerprint(self.source))
                self.assertTrue(self.admit(*fixture(names), plan=plan)["admitted"])

    def test_nonindexed_and_interleaved_geometry_preserve_corners(self):
        for options in ({"indexed": False}, {"interleaved": True},
                        {"indexed": False, "interleaved": True}):
            with self.subTest(options=options):
                self.assertTrue(self.admit(**options)["admitted"])

    def test_array_vertex_triangle_and_cyclic_reordering_passes(self):
        doc, binary = fixture(("C", "A", "B"), mesh_order=("B", "C", "A"),
                              material_order=("C", "B", "A"), reorder_vertices=True,
                              reorder_triangles=True, cycle=1)
        old = doc["accessors"]
        remap = {i: len(old) - 1 - i for i in range(len(old))}
        doc["accessors"] = list(reversed(old))
        for mesh in doc["meshes"]:
            for primitive in mesh["primitives"]:
                primitive["attributes"] = {k: remap[v] for k, v in primitive["attributes"].items()}
                if "indices" in primitive:
                    primitive["indices"] = remap[primitive["indices"]]
        self.assertTrue(self.admit(doc, binary)["admitted"])

    def test_shared_mesh_instances_count_as_distinct_named_nodes(self):
        aliases = {"B": "A"}
        source = self.write(*fixture(aliases=aliases))
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        self.assertTrue(self.admit(*fixture(SELECTED, aliases=aliases), plan=plan)["admitted"])

    def test_invalid_requested_name_sets_fail(self):
        for names in ([], ["A", "A"], list(NAMES), ["Missing"], [""], ["A", " B"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                subset.make_plan(str(self.source), names, fingerprint(self.source))

    def test_missing_duplicate_and_extra_candidate_nodes_fail(self):
        for names in (("A", "B"), ("A", "B", "D"), NAMES):
            with self.subTest(names=names):
                self.reject_document(*fixture(names))
        doc, binary = fixture(SELECTED)
        doc["nodes"][1]["name"] = "A"
        self.reject_document(doc, binary)

    def test_unreferenced_mesh_definition_fails(self):
        doc, binary = fixture(SELECTED)
        doc["meshes"].append(copy.deepcopy(doc["meshes"][0]))
        self.reject_document(doc, binary)

    def test_selected_node_must_be_a_scene_root(self):
        doc, binary = fixture()
        doc["nodes"].append({"name": "Parent", "children": [0]})
        doc["scenes"][0]["nodes"] = [4, 1, 2, 3]
        source = self.write(doc, binary)
        with self.assertRaises(ValueError):
            subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_position_uv_normal_and_winding_mutations_fail(self):
        for change in ("position", "uv", "normal"):
            with self.subTest(change=change):
                self.reject_document(*fixture(SELECTED, change=change))
        self.reject_document(*fixture(SELECTED, reverse_winding=True))

    def test_mesh_label_material_pbr_and_extras_mutations_fail(self):
        for mutation in ("mesh_name", "material_name", "pbr", "emission", "double_sided", "extras"):
            doc, binary = fixture(SELECTED)
            if mutation == "mesh_name": doc["meshes"][0]["name"] = "Renamed"
            elif mutation == "material_name": doc["materials"][0]["name"] = "Renamed"
            elif mutation == "pbr": doc["materials"][0]["pbrMetallicRoughness"]["roughnessFactor"] = .6
            elif mutation == "emission": doc["materials"][2]["emissiveFactor"][0] = .15
            elif mutation == "double_sided": doc["materials"][0]["doubleSided"] = False
            else: doc["nodes"][0]["extras"]["seed"] += 1
            with self.subTest(mutation=mutation):
                self.reject_document(doc, binary)

    def test_translation_rotation_and_scale_mutations_fail(self):
        for field, value in (("translation", [2.1, 0, .25]), ("rotation", [0, 0, 0, 1]),
                             ("scale", [1, 1, 1.1])):
            doc, binary = fixture(SELECTED)
            doc["nodes"][1][field] = value
            with self.subTest(field=field):
                self.reject_document(doc, binary)

    def test_source_and_candidate_pin_mismatches_fail(self):
        candidate = self.write(*fixture(SELECTED))
        for field in ("sha256", "bytes"):
            wrong = fingerprint(self.source)
            wrong[field] = "0" * 64 if field == "sha256" else wrong[field] + 1
            with self.subTest(side="source", field=field), self.assertRaises(ValueError):
                subset.make_plan(str(self.source), list(SELECTED), wrong)
            wrong = fingerprint(candidate)
            wrong[field] = "0" * 64 if field == "sha256" else wrong[field] + 1
            with self.subTest(side="candidate", field=field), self.assertRaises(ValueError):
                subset.admit(self.plan, str(candidate), wrong)

    def test_same_length_nonsemantic_byte_change_requires_new_pin(self):
        doc, binary = fixture(SELECTED, interleaved=True)
        candidate = self.write(doc, binary)
        old = fingerprint(candidate)
        binary[32] ^= 1  # unused in-stride padding; geometry and metadata stay identical
        candidate.write_bytes(pack_glb(doc, binary))
        self.assertEqual(fingerprint(candidate)["bytes"], old["bytes"])
        self.assertNotEqual(fingerprint(candidate)["sha256"], old["sha256"])
        with self.assertRaises(ValueError):
            subset.admit(self.plan, str(candidate), old)
        self.assertTrue(subset.admit(self.plan, str(candidate), fingerprint(candidate))["admitted"])

    def test_source_is_rechecked_after_plan_creation(self):
        doc, binary = fixture(interleaved=True)
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        before = fingerprint(source)
        binary[32] ^= 1
        source.write_bytes(pack_glb(doc, binary))
        self.assertEqual(fingerprint(source)["bytes"], before["bytes"])
        candidate = self.write(*fixture(SELECTED))
        with self.assertRaises(ValueError):
            subset.admit(plan, str(candidate), fingerprint(candidate))

    def test_unsupported_static_payload_members_fail(self):
        mutations = (("images", [{"uri": "external.png"}]), ("textures", [{"source": 0}]),
                     ("animations", [{"channels": [], "samplers": []}]), ("skins", [{"joints": [0]}]),
                     ("extensionsUsed", ["KHR_materials_unlit"]))
        for key, value in mutations:
            doc, binary = fixture(SELECTED)
            doc[key] = value
            with self.subTest(member=key):
                self.reject_document(doc, binary)
        doc, binary = fixture(SELECTED)
        doc["meshes"][0]["primitives"][0]["targets"] = [{"POSITION": 0}]
        self.reject_document(doc, binary)
        doc, binary = fixture(SELECTED)
        doc["accessors"][0]["sparse"] = {"count": 1, "indices": {"bufferView": 0, "componentType": 5123},
                                           "values": {"bufferView": 0}}
        self.reject_document(doc, binary)

    def test_source_and_candidate_files_are_not_modified(self):
        candidate = self.write(*fixture(SELECTED))
        before = (fingerprint(self.source), fingerprint(candidate))
        subset.admit(self.plan, str(candidate), fingerprint(candidate))
        self.assertEqual(before, (fingerprint(self.source), fingerprint(candidate)))

    def test_malformed_source_node_record_raises_public_value_error(self):
        doc, binary = fixture()
        doc["nodes"][0] = None
        source = self.write(doc, binary)
        with self.assertRaises(ValueError):
            subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_malformed_candidate_node_record_raises_public_value_error(self):
        doc, binary = fixture(SELECTED)
        doc["nodes"][0] = None
        self.reject_document(doc, binary)

    def test_misaligned_float_offset_and_stride_fail_during_planning(self):
        for mutation in ("offset", "stride"):
            doc, binary = fixture(interleaved=True)
            primitive = doc["meshes"][0]["primitives"][0]
            position = doc["accessors"][primitive["attributes"]["POSITION"]]
            view = doc["bufferViews"][position["bufferView"]]
            if mutation == "offset":
                position["byteOffset"] = 2
            else:
                view["byteStride"] = 34
            # Both cases fit the view: rejection must not rely on an overrun.
            end = position.get("byteOffset", 0) + (position["count"] - 1) * view["byteStride"] + 12
            self.assertLessEqual(end, view["byteLength"])
            source = self.write(doc, binary)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_normalized_float_position_fails_during_planning(self):
        doc, binary = fixture()
        position = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        doc["accessors"][position]["normalized"] = True
        source = self.write(doc, binary)
        with self.assertRaises(ValueError):
            subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_dangling_material_texture_info_fails_during_planning(self):
        for placement in ("normalTexture", "baseColorTexture"):
            doc, binary = fixture()
            material = doc["materials"][0]
            container = material if placement == "normalTexture" else material["pbrMetallicRoughness"]
            container[placement] = {"index": 0}
            self.assertNotIn("textures", doc)
            source = self.write(doc, binary)
            with self.subTest(placement=placement), self.assertRaises(ValueError):
                subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_accessor_row_cap_boundary_with_tiny_fixture(self):
        # Each indexed fixture has five attribute rows and twelve index rows.
        with patch.object(subset, "MAX_ACCESSOR_ROWS", 12):
            self.assertEqual(subset.make_plan(str(self.source), list(SELECTED),
                                              fingerprint(self.source))["nodes"], list(SELECTED))
        with patch.object(subset, "MAX_ACCESSOR_ROWS", 11), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def test_decoded_scalar_cap_aggregates_selected_meshes(self):
        # Per mesh: POSITION15 + NORMAL15 + UV10 + indices12 = 52 scalars.
        # Three selected meshes total156; every individual accessor is smaller.
        with patch.object(subset, "MAX_DECODED_SCALARS", 156):
            self.assertEqual(subset.make_plan(str(self.source), list(SELECTED),
                                              fingerprint(self.source))["nodes"], list(SELECTED))
        with patch.object(subset, "MAX_DECODED_SCALARS", 155), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def test_triangle_cap_aggregates_selected_meshes(self):
        # Four triangles per mesh: the total is12, rather than4 per inspection.
        with patch.object(subset, "MAX_TRIANGLES", 12):
            self.assertEqual(subset.make_plan(str(self.source), list(SELECTED),
                                              fingerprint(self.source))["nodes"], list(SELECTED))
        with patch.object(subset, "MAX_TRIANGLES", 11), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def test_extra_third_chunk_including_zero_length_fails_planning(self):
        for payload in (b"ABCD", b""):
            source = self.write(*fixture())
            raw = bytearray(source.read_bytes())
            raw.extend(struct.pack("<I4s", len(payload), b"EXTR") + payload)
            struct.pack_into("<I", raw, 8, len(raw))
            source.write_bytes(raw)
            self.assertEqual(struct.unpack_from("<I", raw, 8)[0], len(raw))
            with self.subTest(extra_chunk_bytes=len(payload)), self.assertRaises(ValueError):
                subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_overlong_attribute_name_fails_during_planning(self):
        doc, binary = fixture()
        attributes = doc["meshes"][0]["primitives"][0]["attributes"]
        name = "_" + "A" * 64
        self.assertEqual(len(name), 65)
        attributes[name] = attributes["NORMAL"]
        source = self.write(doc, binary)
        with self.assertRaises(ValueError):
            subset.make_plan(str(source), list(SELECTED), fingerprint(source))

    def test_attribute_count_cap_with_tiny_fixture(self):
        with patch.object(subset, "MAX_ATTRIBUTES", 3):
            self.assertEqual(subset.make_plan(str(self.source), list(SELECTED),
                                              fingerprint(self.source))["nodes"], list(SELECTED))
        with patch.object(subset, "MAX_ATTRIBUTES", 2), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def test_canonical_work_cap_with_tiny_fixture(self):
        with patch.object(subset, "MAX_CANONICAL_BYTES", 256), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))
        self.assertEqual(subset.make_plan(str(self.source), list(SELECTED),
                                          fingerprint(self.source))["nodes"], list(SELECTED))

    def test_json_chunk_cap_without_large_allocation(self):
        with patch.object(subset, "MAX_JSON_BYTES", 64), self.assertRaises(ValueError):
            subset.make_plan(str(self.source), list(SELECTED), fingerprint(self.source))

    def test_cli_plan_and_admit_emit_only_json_and_remain_not_native_ready(self):
        made = self.cli(self.plan_arguments())
        self.assertEqual(made.returncode, 0, made.stderr)
        plan = json.loads(made.stdout)
        self.assertEqual(plan["schema"], "daedalus.static-subset.v1")
        plan_path = self.directory / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        candidate = self.write(*fixture(SELECTED))
        pin = fingerprint(candidate)
        checked = self.cli(["admit", "--plan", str(plan_path), "--candidate", str(candidate),
                            "--sha256", pin["sha256"], "--bytes", str(pin["bytes"])])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        report = json.loads(checked.stdout)
        self.assertIs(report["admitted"], True)
        self.assertIs(report["native_ready"], False)

    def test_cli_bad_pin_fails_and_has_no_output_file_option(self):
        args = self.plan_arguments()
        args[args.index("--sha256") + 1] = "0" * 64
        self.assertNotEqual(self.cli(args).returncode, 0)
        forbidden = self.directory / "must-not-exist.json"
        failed = self.cli(self.plan_arguments() + ["--out", str(forbidden)])
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SubsetTests))
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print("%d/%d" % (max(0, passed), result.testsRun))
    sys.exit(0 if result.wasSuccessful() else 1)
