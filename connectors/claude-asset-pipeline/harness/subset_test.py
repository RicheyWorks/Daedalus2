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


def unpack_glb(path):
    """Independent fixture reader; does not call producer/admission internals."""
    raw = Path(path).read_bytes()
    if len(raw) < 28 or struct.unpack_from("<4sII", raw) != (b"glTF", 2, len(raw)):
        raise AssertionError("Produced file has an invalid GLB header")
    chunks, offset = [], 12
    while offset < len(raw):
        length, kind = struct.unpack_from("<I4s", raw, offset)
        offset += 8
        if length % 4 or offset + length > len(raw):
            raise AssertionError("Produced file has an invalid chunk range")
        chunks.append((kind, raw[offset:offset + length]))
        offset += length
    if [kind for kind, _ in chunks] != [b"JSON", b"BIN\0"]:
        raise AssertionError("Produced file must contain exactly JSON and BIN")
    doc = json.loads(chunks[0][1])
    length = doc["buffers"][0]["byteLength"]
    if not 0 <= len(chunks[1][1]) - length <= 3:
        raise AssertionError("Produced buffer length differs from BIN")
    return doc, chunks[1][1][:length]


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

    def assert_export_preserved(self, plan, output):
        """Follow both dependency graphs independently and compare raw views."""
        source, source_bin = unpack_glb(plan["source"]["path"])
        made, made_bin = unpack_glb(output)
        wanted = {n["name"]: n for n in source["nodes"] if n.get("name") in plan["nodes"]}
        actual = {n["name"]: n for n in made["nodes"]}
        self.assertEqual(set(actual), set(plan["nodes"]))
        self.assertEqual(len(made["nodes"]), len(plan["nodes"]))
        self.assertEqual(len(made["scenes"]), 1)
        self.assertEqual(set(made["scenes"][made.get("scene", 0)]["nodes"]), set(range(len(actual))))
        mappings = {key: {} for key in ("meshes", "materials", "accessors", "bufferViews")}

        def pair(label, old, new):
            previous = mappings[label].setdefault(old, new)
            self.assertEqual(previous, new, "shared %s reference was duplicated" % label)
            self.assertEqual(len(set(mappings[label].values())), len(mappings[label]),
                             "distinct source %s definitions were merged" % label)

        def compare_accessor(old_index, new_index):
            pair("accessors", old_index, new_index)
            old, new = source["accessors"][old_index], made["accessors"][new_index]
            self.assertEqual({k: v for k, v in old.items() if k != "bufferView"},
                             {k: v for k, v in new.items() if k != "bufferView"})
            old_view, new_view = old["bufferView"], new["bufferView"]
            pair("bufferViews", old_view, new_view)
            a, b = source["bufferViews"][old_view], made["bufferViews"][new_view]
            self.assertEqual({k: v for k, v in a.items() if k not in ("buffer", "byteOffset")},
                             {k: v for k, v in b.items() if k not in ("buffer", "byteOffset")})
            self.assertEqual(b.get("buffer", 0), 0)
            self.assertEqual(b.get("byteOffset", 0) % 4, 0)
            old_start, new_start = a.get("byteOffset", 0), b.get("byteOffset", 0)
            self.assertEqual(source_bin[old_start:old_start + a["byteLength"]],
                             made_bin[new_start:new_start + b["byteLength"]])

        for name in plan["nodes"]:
            old, new = wanted[name], actual[name]
            self.assertEqual({k: v for k, v in old.items() if k != "mesh"},
                             {k: v for k, v in new.items() if k != "mesh"})
            pair("meshes", old["mesh"], new["mesh"])
            a, b = source["meshes"][old["mesh"]], made["meshes"][new["mesh"]]
            self.assertEqual({k: v for k, v in a.items() if k != "primitives"},
                             {k: v for k, v in b.items() if k != "primitives"})
            self.assertEqual(len(a["primitives"]), len(b["primitives"]))
            for ap, bp in zip(a["primitives"], b["primitives"]):
                references = ("attributes", "indices", "material")
                self.assertEqual({k: v for k, v in ap.items() if k not in references},
                                 {k: v for k, v in bp.items() if k not in references})
                self.assertEqual(set(ap["attributes"]), set(bp["attributes"]))
                for semantic in ap["attributes"]:
                    compare_accessor(ap["attributes"][semantic], bp["attributes"][semantic])
                self.assertEqual("indices" in ap, "indices" in bp)
                if "indices" in ap:
                    compare_accessor(ap["indices"], bp["indices"])
                self.assertEqual("material" in ap, "material" in bp)
                if "material" in ap:
                    pair("materials", ap["material"], bp["material"])
                    self.assertEqual(source["materials"][ap["material"]], made["materials"][bp["material"]])
        for label, mapping in mappings.items():
            self.assertEqual(len(made.get(label, [])), len(mapping), "extra " + label)
        view_bytes = sum(v["byteLength"] for v in made["bufferViews"])
        self.assertGreaterEqual(len(made_bin), view_bytes)
        self.assertLessEqual(len(made_bin), view_bytes + 3 * len(made["bufferViews"]))
        self.assertEqual(len(made["buffers"]), 1)
        self.assertNotIn("uri", made["buffers"][0])
        for unsupported in ("images", "textures", "animations", "skins", "extensionsUsed", "extensionsRequired"):
            self.assertFalse(made.get(unsupported))
        return made

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

    def test_producer_receipt_and_raw_binary_preservation(self):
        output = self.directory / "selected.glb"
        before = fingerprint(self.source)
        receipt = subset.export_subset(self.plan, str(output))
        self.assertEqual(receipt["schema"], "daedalus.static-subset-export.v1")
        self.assertIs(receipt["exported"], True)
        self.assertEqual(receipt["producer"], "pinned-glb-byte-extraction")
        self.assertIs(receipt["native_ready"], False)
        self.assertEqual(receipt["nodes"], list(SELECTED))
        self.assertIs(receipt["admission"]["admitted"], True)
        self.assertIs(receipt["admission"]["native_ready"], False)
        self.assertEqual({k: receipt["candidate"][k] for k in ("sha256", "bytes")}, fingerprint(output))
        self.assertEqual(Path(receipt["candidate"]["path"]).resolve(), output.resolve())
        self.assertEqual(json.loads(json.dumps(receipt)), receipt)
        self.assert_export_preserved(self.plan, output)
        self.assertEqual(fingerprint(self.source), before)

    def test_producer_follows_distant_shared_index_accessor(self):
        doc, binary = fixture()
        distant = doc["meshes"][3]["primitives"][0]["indices"]
        doc["meshes"][2]["primitives"][0]["indices"] = distant
        self.assertGreater(distant, max(doc["meshes"][2]["primitives"][0]["attributes"].values()))
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        output = self.directory / "distant.glb"
        subset.export_subset(plan, str(output))
        self.assert_export_preserved(plan, output)

    def test_producer_preserves_interleaved_views_and_shared_mesh_nodes(self):
        for options in ({"interleaved": True}, {"aliases": {"B": "A"}},
                        {"interleaved": True, "aliases": {"B": "A"}}):
            with self.subTest(options=options):
                source = self.write(*fixture(**options))
                plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
                self.serial += 1
                output = self.directory / ("produced-%02d.glb" % self.serial)
                subset.export_subset(plan, str(output))
                self.assert_export_preserved(plan, output)

    def test_producer_preserves_nonindexed_geometry(self):
        source = self.write(*fixture(indexed=False, interleaved=True))
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        output = self.directory / "nonindexed.glb"
        subset.export_subset(plan, str(output))
        made = self.assert_export_preserved(plan, output)
        self.assertTrue(all("indices" not in p for m in made["meshes"] for p in m["primitives"]))

    def test_producer_realigns_short_copied_views(self):
        doc, binary = fixture()
        indices = doc["meshes"][0]["primitives"][0]["indices"]
        doc["accessors"][indices]["count"] = 3
        doc["bufferViews"][doc["accessors"][indices]["bufferView"]]["byteLength"] = 6
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        output = self.directory / "alignment.glb"
        subset.export_subset(plan, str(output))
        self.assert_export_preserved(plan, output)

    def test_producer_bytes_are_deterministic_across_output_names(self):
        first, second = self.directory / "first.glb", self.directory / "second.glb"
        subset.export_subset(self.plan, str(first))
        subset.export_subset(self.plan, str(second))
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_producer_refuses_existing_target_without_changes(self):
        output = self.directory / "retained.glb"
        output.write_bytes(b"retained preexisting artifact")
        before = output.read_bytes(), fingerprint(self.source), set(self.directory.iterdir())
        with self.assertRaises((ValueError, FileExistsError)):
            subset.export_subset(self.plan, str(output))
        self.assertEqual(before, (output.read_bytes(), fingerprint(self.source), set(self.directory.iterdir())))

    def test_producer_refuses_source_as_output_without_changes(self):
        before = self.source.read_bytes()
        with self.assertRaises((ValueError, FileExistsError)):
            subset.export_subset(self.plan, str(self.source))
        self.assertEqual(self.source.read_bytes(), before)

    def test_producer_refuses_source_drift_and_bad_plan_without_output(self):
        invalid = copy.deepcopy(self.plan)
        invalid["schema"] = "wrong"
        output = self.directory / "bad-plan.glb"
        with self.assertRaises(ValueError):
            subset.export_subset(invalid, str(output))
        self.assertFalse(output.exists())
        doc, binary = fixture(interleaved=True)
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        binary[32] ^= 1
        source.write_bytes(pack_glb(doc, binary))
        output = self.directory / "drift.glb"
        with self.assertRaises(ValueError):
            subset.export_subset(plan, str(output))
        self.assertFalse(output.exists())

    def test_cli_producer_exports_then_admits_the_actual_file(self):
        plan_path = self.directory / "producer-plan.json"
        plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        output = self.directory / "cli-selected.glb"
        exported = self.cli(["export", "--plan", str(plan_path), "--output", str(output)])
        self.assertEqual(exported.returncode, 0, exported.stderr)
        receipt = json.loads(exported.stdout)
        self.assertIs(receipt["exported"], True)
        self.assertIs(receipt["native_ready"], False)
        pin = fingerprint(output)
        self.assertEqual({k: receipt["candidate"][k] for k in ("sha256", "bytes")}, pin)
        self.assert_export_preserved(self.plan, output)
        checked = self.cli(["admit", "--plan", str(plan_path), "--candidate", str(output),
                            "--sha256", pin["sha256"], "--bytes", str(pin["bytes"])])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIs(json.loads(checked.stdout)["admitted"], True)

    def test_cli_producer_failures_exit_two_and_preserve_existing_files(self):
        plan_path = self.directory / "producer-plan.json"
        plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        output = self.directory / "cli-existing.glb"
        output.write_bytes(b"keep exactly these bytes")
        before = fingerprint(output)
        failed = self.cli(["export", "--plan", str(plan_path), "--output", str(output)])
        self.assertEqual(failed.returncode, 2, failed.stderr)
        self.assertEqual(fingerprint(output), before)
        invalid = copy.deepcopy(self.plan)
        invalid["schema"] = "wrong"
        plan_path.write_text(json.dumps(invalid), encoding="utf-8")
        fresh = self.directory / "cli-invalid.glb"
        failed = self.cli(["export", "--plan", str(plan_path), "--output", str(fresh)])
        self.assertEqual(failed.returncode, 2, failed.stderr)
        self.assertFalse(fresh.exists())
        # Valid JSON and unchanged length do not excuse a source hash change.
        doc, binary = fixture(interleaved=True)
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        binary[32] ^= 1
        source.write_bytes(pack_glb(doc, binary))
        failed = self.cli(["export", "--plan", str(plan_path), "--output", str(fresh)])
        self.assertEqual(failed.returncode, 2, failed.stderr)
        self.assertFalse(fresh.exists())

    def test_geometry_identity_bounds_use_referenced_corners_and_default_is_unchanged(self):
        def only_first_face(doc, binary):
            index = doc["meshes"][0]["primitives"][0]["indices"]
            accessor = doc["accessors"][index]
            view = doc["bufferViews"][accessor["bufferView"]]
            start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            struct.pack_into("<12H", binary, start, *([0, 1, 4] * 4))
        doc, binary = fixture()
        only_first_face(doc, binary)
        source = self.write(doc, binary)
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        doc, binary = fixture(SELECTED)
        only_first_face(doc, binary)
        candidate = self.write(doc, binary)
        default = subset.admit(plan, str(candidate), fingerprint(candidate))
        self.assertNotIn("geometry", default)
        report = subset.admit(plan, str(candidate), fingerprint(candidate), include_geometry=True)
        geometry = report["geometry"]
        self.assertEqual(geometry["coordinate_system"], {
            "distance_unit": "metre", "up_axis": "+Y", "handedness": "right",
            "native_conversion_verified": False})
        a = next(n for n in geometry["nodes"] if n["name"] == "A")
        # Unused POSITION rows still reach Y1 in the accessor bounds. The
        # actual referenced face reaches only Y0.4 and must control this report.
        self.assertEqual(a["local_bounds"]["min"], [-1., 0., 0.])
        self.assertAlmostEqual(a["local_bounds"]["max"][1], .4, places=6)
        self.assertAlmostEqual(a["local_bounds"]["size"][1], .4, places=6)
        self.assertEqual(a["local_bounds"], a["world_bounds"])
        self.assertEqual(a["triangles"], 4)
        self.assertEqual(a["transform"], {"translation": [0, 0, 0],
                                          "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]})
        self.assertIs(report["native_ready"], False)

    def test_geometry_quaternion_bounds_match_analytic_rotation_and_world_union(self):
        candidate = self.write(*fixture(SELECTED))
        geometry = subset.admit(self.plan, str(candidate), fingerprint(candidate),
                                include_geometry=True)["geometry"]
        b = next(n for n in geometry["nodes"] if n["name"] == "B")
        cosine, sine = math.cos(.2), math.sin(.2)
        expected = {"min": [2 - cosine - sine, -sine, .25],
                    "max": [2 + cosine, sine + cosine, .25],
                    "size": [2 * cosine + sine, cosine + 2 * sine, 0.]}
        for key in expected:
            for actual, wanted in zip(b["world_bounds"][key], expected[key]):
                self.assertAlmostEqual(actual, wanted, places=6)
        self.assertEqual(b["local_bounds"], {"min": [-1., 0., 0.], "max": [1., 1., 0.],
                                             "size": [2., 1., 0.]})
        union = {"min": [-1., -sine, 0.], "max": [4 + cosine, sine + cosine, .5]}
        for key in union:
            for actual, wanted in zip(geometry["world_bounds"][key], union[key]):
                self.assertAlmostEqual(actual, wanted, places=6)

    def test_geometry_affine_matrix_translation_and_negative_scale(self):
        matrix = [-2., 0., 0., 0., 0., 3., 0., 0., 0., 0., 1., 0., 4., -5., 6., 1.]
        def transformed(names):
            doc, binary = fixture(names)
            b = next(n for n in doc["nodes"] if n["name"] == "B")
            for key in ("translation", "rotation", "scale"):
                b.pop(key, None)
            b["matrix"] = list(matrix)
            return doc, binary
        source = self.write(*transformed(NAMES))
        plan = subset.make_plan(str(source), list(SELECTED), fingerprint(source))
        candidate = self.write(*transformed(SELECTED))
        geometry = subset.admit(plan, str(candidate), fingerprint(candidate),
                                include_geometry=True)["geometry"]
        b = next(n for n in geometry["nodes"] if n["name"] == "B")
        self.assertEqual(b["transform"], {"matrix": matrix})
        self.assertEqual(b["world_bounds"], {"min": [2., -5., 6.], "max": [6., -2., 6.],
                                             "size": [4., 3., 0.]})

    def test_geometry_retains_raw_pbr_extras_and_material_binding_facts(self):
        doc, binary = fixture(SELECTED)
        candidate = self.write(doc, binary)
        geometry = subset.admit(self.plan, str(candidate), fingerprint(candidate),
                                include_geometry=True)["geometry"]
        nodes = {n["name"]: n for n in geometry["nodes"]}
        for index, name in enumerate(SELECTED):
            node = nodes[name]
            self.assertEqual(node["node_index"], index)
            self.assertEqual(node["mesh_index"], index)
            self.assertEqual(node["mesh_name"], "GenericMesh_" + name)
            self.assertEqual(node["node_extras"], doc["nodes"][index]["extras"])
            self.assertEqual(node["primitive_material_indices"], [index])
            self.assertEqual(node["source_material_slots"], 1)
            self.assertEqual(node["materials"], [{"index": index, "name": "Mat_" + name,
                                                  "definition": doc["materials"][index]}])
        self.assertEqual(nodes["C"]["materials"][0]["definition"]["emissiveFactor"], [.1, .2, .3])

    def test_cli_geometry_flag_is_optional_and_emits_actual_bounds(self):
        plan_path = self.directory / "geometry-plan.json"
        plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        candidate = self.write(*fixture(SELECTED))
        pin = fingerprint(candidate)
        args = ["admit", "--plan", str(plan_path), "--candidate", str(candidate),
                "--sha256", pin["sha256"], "--bytes", str(pin["bytes"])]
        default = self.cli(args)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertNotIn("geometry", json.loads(default.stdout))
        detailed = self.cli(args + ["--geometry"])
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        report = json.loads(detailed.stdout)
        self.assertEqual(len(report["geometry"]["nodes"]), 3)
        self.assertEqual(report["geometry"]["coordinate_system"]["distance_unit"], "metre")
        self.assertIs(report["geometry"]["coordinate_system"]["native_conversion_verified"], False)
        self.assertIs(report["native_ready"], False)

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
