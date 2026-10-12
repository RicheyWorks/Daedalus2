# SPDX-License-Identifier: MIT
"""Saved-GLB handoff contracts, entirely in process: no sockets or editor processes.

Run from the pipeline folder: python harness/ship_saved_test.py
"""
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import ship_saved as saved, sides, wire

PROJECT_PARENT = "/Game/Daedalus/Materials/Gltf/MI_Wood.MI_Wood"
NANITE_CHECK = "every material is ready for Nanite (on the project's base, not the engine plugin's)"


def glb_bytes(parts, *, node_scale=None):
    """A valid GLB2 container with actual position/index data and explicit bounds."""
    doc = {"asset": {"version": "2.0"}, "buffers": [], "bufferViews": [],
           "accessors": [], "materials": [], "meshes": [], "nodes": [],
           "scenes": [{"nodes": list(range(len(parts)))}], "scene": 0}
    binary = bytearray()
    materials = []
    for part in parts:
        for material in part["materials"]:
            if material not in materials:
                materials.append(material)
    doc["materials"] = [{"name": material} for material in materials]

    def accessor(data, count, component_type, kind, **bounds):
        binary.extend(b"\0" * (-len(binary) % 4))
        offset = len(binary)
        binary.extend(data)
        view = len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        index = len(doc["accessors"])
        doc["accessors"].append(dict(bufferView=view, componentType=component_type,
                                     count=count, type=kind, **bounds))
        return index

    for part in parts:
        x, y, z = part["dims"]
        positions = struct.pack("<9f", 0, 0, 0, x, 0, 0, 0, y, z)
        pos = accessor(positions, 3, 5126, "VEC3", min=[0, 0, 0], max=[x, y, z])
        primitives = []
        slot_count = len(part["materials"]) or 1
        for slot in range(slot_count):
            count = part["tris"] // slot_count + (slot < part["tris"] % slot_count)
            indices = accessor(struct.pack("<%dH" % (count * 3), *([0, 1, 2] * count)),
                               count * 3, 5123, "SCALAR")
            primitive = {"attributes": {"POSITION": pos}, "indices": indices, "mode": 4}
            if part["materials"]:
                primitive["material"] = materials.index(part["materials"][slot])
            primitives.append(primitive)
        mesh_index = len(doc["meshes"])
        doc["meshes"].append({"name": part["name"], "primitives": primitives})
        node = {"name": part["name"], "mesh": mesh_index}
        if node_scale is not None:
            node["scale"] = node_scale
        doc["nodes"].append(node)
    doc["buffers"] = [{"byteLength": len(binary)}]
    body = json.dumps(doc).encode("utf-8")
    body += b" " * (-len(body) % 4)
    binary.extend(b"\0" * (-len(binary) % 4))
    length = 12 + 8 + len(body) + 8 + len(binary)
    return (struct.pack("<4sII", b"glTF", 2, length)
            + struct.pack("<I4s", len(body), b"JSON") + body
            + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def import_params(code):
    """Read the script's JSON parameter binding without executing editor code."""
    for statement in ast.parse(code).body:
        if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PARAMS" for target in statement.targets):
            return json.loads(ast.literal_eval(statement.value))
    raise AssertionError("import script has no JSON PARAMS binding")


def alter_document(data, mutate):
    length, kind = struct.unpack_from("<I4s", data, 12)
    assert kind == b"JSON"
    document = json.loads(data[20:20 + length])
    mutate(document)
    body = json.dumps(document).encode("utf-8")
    body += b" " * (-len(body) % 4)
    rest = data[20 + length:]
    total = 12 + 8 + len(body) + len(rest)
    return struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(body), b"JSON") + body + rest


class Fixture(unittest.TestCase):
    def setUp(self):
        network_guard = mock.patch("socket.create_connection",
                                   side_effect=AssertionError("offline contract test attempted a socket"))
        network_guard.start()
        self.addCleanup(network_guard.stop)
        self.temp = tempfile.TemporaryDirectory(prefix="saved-glb-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "art"
        (self.root / "glb").mkdir(parents=True)
        (self.root / "jobs").mkdir()
        self.asset = "Tool_Contract"
        self.job_path = self.root / "jobs" / (self.asset + ".json")
        self.source = self.root / "glb" / (self.asset + ".glb")
        self.dest = "/Game/Daedalus/Art/Tool/" + self.asset
        self.make_fixture()

    def make_fixture(self, parts=None, *, node_scale=None):
        self.parts = parts or [{"name": self.asset, "tris": 2,
                                "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]}]
        self.source.write_bytes(glb_bytes(self.parts, node_scale=node_scale))
        materials = list(dict.fromkeys(m for p in self.parts for m in p["materials"]))
        self.job = {"spec": 1, "asset": self.asset, "kind": "Tool", "blender": {
            "blend": str(self.root / "Tool" / (self.asset + ".blend")),
            "glb": str(self.source), "glb_sha1": hashlib.sha1(self.source.read_bytes()).hexdigest(),
            "tris": sum(p["tris"] for p in self.parts),
            "meshes": [{"name": p["name"], "tris": p["tris"], "materials": p["materials"],
                        "dims_m": p["dims"]} for p in self.parts],
            "materials": materials, "selfcheck": {"ok": True, "fails": []},
            "built_by": "fixture builder", "private_extension": {"keep": [1, 2]}},
            "unreal": {"result": "previous result", "extension": "retain me"},
            "last_result": {"event": "previous event"}, "another_owner": {"notes": ["keep"]}}
        self.write_job()

    def write_job(self):
        self.job_path.write_text(json.dumps(self.job, indent=2), encoding="utf-8")

    def made(self, dest=None):
        dest = dest or self.dest
        meshes = [{"name": p["name"], "path": dest + "/" + p["name"],
                   "triangles": p["tris"], "render_triangles": p["tris"], "nanite": False,
                   "materials": p["materials"][:], "dims_cm": [d * 100 for d in p["dims"]]}
                  for p in self.parts]
        names = list(dict.fromkeys(m for p in self.parts for m in p["materials"]))
        return {"dest": dest, "imported": [m["path"] for m in meshes], "meshes": meshes,
                "materials": [{"name": n, "path": dest + "/M_" + n, "parent": PROJECT_PARENT} for n in names]}

    def reject_before_editor(self, *, asset=None):
        with mock.patch.object(wire, "call") as call:
            with self.assertRaises((ValueError, OSError)):
                saved.ship_saved(str(self.job_path), asset=asset, handoff_root=str(self.root))
        call.assert_not_called()

    def run_mock_import(self, made=None, **kwargs):
        snapshots = []
        expected_bytes = self.source.read_bytes()
        outcome = copy.deepcopy(self.made() if made is None else made)

        def bridge(addr, command, timeout=600, side="bridge", **params):
            self.assertEqual(addr, kwargs.get("unreal", wire.UNREAL))
            self.assertEqual(command, "execute_python")
            self.assertEqual(side, "Unreal")
            self.assertEqual(timeout, kwargs.get("timeout", 600))
            bound = import_params(params["code"])
            snapshot = Path(bound["path"])
            snapshots.append(snapshot)
            self.assertNotEqual(snapshot.resolve(), self.source.resolve())
            self.assertEqual(snapshot.read_bytes(), expected_bytes)
            self.assertEqual(bound["dest"], outcome["dest"])
            self.assertEqual(bound["save"], kwargs.get("save", True))
            return {"result": outcome}

        with mock.patch.object(wire, "call", side_effect=bridge) as call:
            result = saved.ship_saved(str(self.job_path), handoff_root=str(self.root), **kwargs)
        call.assert_called_once()
        self.assertTrue(snapshots)
        self.assertTrue(all(p.is_file() and p.read_bytes() == expected_bytes for p in snapshots))
        digest = hashlib.sha1(expected_bytes).hexdigest()
        self.assertEqual(snapshots, [self.root / "import-cache" / digest / (self.asset + ".glb")])
        self.assertTrue(result["provenance"]["snapshot_retained"], "Unreal Reimport needs the verified source")
        return result


class SavedHandoffTests(Fixture):
    def test_valid_glb_uses_one_unreal_call_and_preserves_original_files(self):
        source_before, job_before = self.source.read_bytes(), self.job_path.read_bytes()
        result = self.run_mock_import()
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["checks"]), 12)  # Current ten-check judge plus budget and slot gates.
        self.assertTrue(next(c for c in result["checks"] if c["check"] == NANITE_CHECK)["ok"])
        self.assertTrue(all(c["ok"] for c in result["checks"]))
        self.assertEqual(result["dest"], self.dest)
        self.assertEqual(Path(result["path"]).resolve(), self.source.resolve())
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(self.job_path.read_bytes(), job_before)

    def test_multiple_meshes_keep_independent_geometry_and_material_checks(self):
        self.make_fixture([
            {"name": self.asset + "_Handle", "tris": 2, "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]},
            {"name": self.asset + "_Head", "tris": 4, "materials": ["Stone", "Trim"], "dims": [0.6, 0.2, 0.1]}])
        result = self.run_mock_import()
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["unreal"]["meshes"]), 2)

    def test_node_and_mesh_data_names_can_differ_when_explicitly_linked(self):
        changed = alter_document(self.source.read_bytes(),
                                 lambda d: d["meshes"][0].update(name=self.asset + ".001"))
        self.source.write_bytes(changed)
        self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
        self.job["blender"]["meshes"][0]["name"] = self.asset + ".001"
        self.write_job()
        result = self.run_mock_import()
        self.assertTrue(result["ok"], result)

    def test_duplicate_or_instanced_nodes_cannot_inflate_a_manifest_mesh(self):
        changed = alter_document(self.source.read_bytes(),
                                 lambda d: d["nodes"].append(dict(d["nodes"][0], name=self.asset + "_Instance")))
        self.source.write_bytes(changed)
        self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
        self.write_job()
        self.reject_before_editor()
        self.make_fixture([
            {"name": self.asset + "_Handle", "tris": 2, "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]},
            {"name": self.asset + "_Head", "tris": 4, "materials": ["Stone"], "dims": [0.6, 0.2, 0.1]}])
        changed = alter_document(self.source.read_bytes(),
                                 lambda d: d["nodes"][1].update(name=d["nodes"][0]["name"]))
        self.source.write_bytes(changed)
        self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
        self.write_job()
        self.reject_before_editor()

    def test_custom_destination_and_transport_are_forwarded(self):
        destination = "/Game/ContractTests/Imports"
        result = self.run_mock_import(self.made(destination + "/" + self.asset),
                                      dest=destination, save=False, unreal=("mock-host", 12345), timeout=37)
        self.assertTrue(result["ok"])
        self.assertEqual(result["dest"], destination + "/" + self.asset)

    def test_game_root_is_a_valid_parent_destination(self):
        result = self.run_mock_import(self.made("/Game/" + self.asset), dest="/Game")
        self.assertTrue(result["ok"])
        self.assertEqual(result["dest"], "/Game/" + self.asset)

    def test_hash_mismatch_prevents_any_editor_work(self):
        self.source.write_bytes(self.source.read_bytes() + b"changed since READY")
        self.reject_before_editor()

    def test_missing_file_and_corrupt_glb_are_refused(self):
        original = self.source.read_bytes()
        self.source.unlink()
        self.reject_before_editor()
        for broken in (b"not a GLB", original[:12], original[:19]):
            with self.subTest(length=len(broken)):
                self.source.write_bytes(broken)
                self.job["blender"]["glb_sha1"] = hashlib.sha1(broken).hexdigest()
                self.write_job()
                self.reject_before_editor()

    def test_inconsistent_container_header_is_refused(self):
        original = self.source.read_bytes()
        for declared_length in (12, len(original) + 4):
            with self.subTest(declared_length=declared_length):
                broken = original[:8] + struct.pack("<I", declared_length) + original[12:]
                self.source.write_bytes(broken)
                self.job["blender"]["glb_sha1"] = hashlib.sha1(broken).hexdigest()
                self.write_job()
                self.reject_before_editor()

    def test_glb_buffer_requires_matching_embedded_binary_data(self):
        original = self.source.read_bytes()
        json_length = struct.unpack_from("<I", original, 12)[0]
        json_end = 20 + json_length
        without_bin = original[:8] + struct.pack("<I", json_end) + original[12:json_end]
        oversized = alter_document(original, lambda d: d["buffers"][0].update(byteLength=10 ** 6))
        for changed in (without_bin, oversized):
            with self.subTest(length=len(changed)):
                self.source.write_bytes(changed)
                self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
                self.write_job()
                self.reject_before_editor()

    def test_binary_ranges_and_geometry_references_cannot_point_outside_the_file(self):
        original = self.source.read_bytes()
        mutations = {
            "bufferView too long": lambda d: d["bufferViews"][0].update(byteLength=10 ** 6),
            "missing accessor": lambda d: d["meshes"][0]["primitives"][0]["attributes"].update(POSITION=999),
            "negative index": lambda d: d["meshes"][0]["primitives"][0].update(indices=-1),
            "invalid accessor count": lambda d: d["accessors"][0].update(count=-3),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                changed = alter_document(original, mutate)
                self.source.write_bytes(changed)
                self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
                self.write_job()
                self.reject_before_editor()

    def test_manifest_spec_asset_kind_and_expected_identity_are_checked(self):
        baseline = copy.deepcopy(self.job)
        for field, bad in (("spec", 2), ("spec", True), ("asset", "Tool_Other"),
                           ("kind", "Mob"), ("kind", "Unknown")):
            with self.subTest(field=field, value=bad):
                self.job = copy.deepcopy(baseline)
                self.job[field] = bad
                self.write_job()
                self.reject_before_editor()
        self.job = baseline
        self.write_job()
        self.reject_before_editor(asset="Tool_Other")

    def test_selfcheck_must_be_true_and_have_no_failures(self):
        for selfcheck in ({"ok": False, "fails": []}, {"ok": "true", "fails": []},
                          {"ok": True, "fails": ["unapplied scale"]}, {}, None):
            with self.subTest(selfcheck=selfcheck):
                self.job["blender"]["selfcheck"] = selfcheck
                self.write_job()
                self.reject_before_editor()

    def test_source_and_job_must_stay_within_the_handoff_contract(self):
        outside = Path(self.temp.name) / (self.asset + ".glb")
        outside.write_bytes(self.source.read_bytes())
        self.job["blender"]["glb"] = str(outside)
        self.write_job()
        self.reject_before_editor()
        self.job["blender"]["glb"] = str(self.root / "glb" / ".." / ".." / (self.asset + ".glb"))
        self.write_job()
        self.reject_before_editor()
        self.job["blender"]["glb"] = str(self.source)
        self.write_job()
        moved_job = Path(self.temp.name) / (self.asset + ".json")
        moved_job.write_bytes(self.job_path.read_bytes())
        with mock.patch.object(wire, "call") as call:
            with self.assertRaises((ValueError, OSError)):
                saved.ship_saved(str(moved_job), handoff_root=str(self.root))
        call.assert_not_called()

    def test_manifest_mesh_facts_are_compared_with_the_saved_file(self):
        baseline = copy.deepcopy(self.job)
        for field, bad in (("name", "Tool_Other"), ("tris", 3),
                           ("materials", ["Unrelated"]), ("dims_m", [9.0, 0.3, 0.1])):
            with self.subTest(field=field):
                self.job = copy.deepcopy(baseline)
                self.job["blender"]["meshes"][0][field] = bad
                self.write_job()
                self.reject_before_editor()
        for field, bad in (("tris", 999), ("materials", ["Unrelated"]), ("meshes", [])):
            with self.subTest(aggregate=field):
                self.job = copy.deepcopy(baseline)
                self.job["blender"][field] = bad
                self.write_job()
                self.reject_before_editor()

    def test_duplicate_manifest_meshes_and_nonfinite_dimensions_are_refused(self):
        baseline = copy.deepcopy(self.job)
        self.job["blender"]["meshes"].append(copy.deepcopy(self.job["blender"]["meshes"][0]))
        self.job["blender"]["tris"] *= 2
        self.write_job()
        self.reject_before_editor()
        for bad in (float("nan"), float("inf"), -1.0, 10 ** 1000):
            with self.subTest(dimension_type=type(bad).__name__):
                self.job = copy.deepcopy(baseline)
                self.job["blender"]["meshes"][0]["dims_m"][0] = bad
                self.write_job()
                self.reject_before_editor()

    def test_malformed_dependencies_and_missing_file_identity_are_refused(self):
        original = self.source.read_bytes()
        mutations = {
            "buffers not a list": lambda d: d.update(buffers={"byteLength": 3}),
            "images not a list": lambda d: d.update(images=42),
            "external buffer": lambda d: d.update(buffers=[{"uri": "other.bin", "byteLength": 3}]),
            "external image": lambda d: d.update(images=[{"uri": "other.png"}]),
            "missing node": lambda d: d.update(nodes=[]),
            "wrong mesh name": lambda d: d["meshes"][0].update(name="Tool_Other"),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                changed = alter_document(original, mutate)
                self.source.write_bytes(changed)
                self.job["blender"]["glb_sha1"] = hashlib.sha1(changed).hexdigest()
                self.write_job()
                self.reject_before_editor()

    def test_budget_material_slot_and_node_scale_fail_before_import(self):
        cases = [({"name": self.asset, "tris": 3001, "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]}, None),
                 ({"name": self.asset, "tris": 4, "materials": ["A", "B", "C", "D"], "dims": [0.9, 0.3, 0.1]}, None),
                 ({"name": self.asset, "tris": 2, "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]}, [2, 1, 1])]
        for part, scale in cases:
            with self.subTest(triangles=part["tris"], slots=len(part["materials"]), scale=scale):
                self.make_fixture([part], node_scale=scale)
                self.reject_before_editor()

    def test_unreal_geometry_material_and_dimension_losses_cannot_ship(self):
        self.make_fixture([
            {"name": self.asset + "_Handle", "tris": 2, "materials": ["Wood"], "dims": [0.9, 0.3, 0.1]},
            {"name": self.asset + "_Head", "tris": 4, "materials": ["Stone"], "dims": [0.6, 0.2, 0.1]}])
        faults = {
            "missing mesh": lambda m: m["meshes"].pop(),
            "lost triangle": lambda m: m["meshes"][0].update(triangles=1),
            "lost slot": lambda m: m["meshes"][0].update(materials=[]),
            "wrong size": lambda m: m["meshes"][0].update(dims_cm=[900, 30, 10]),
            "lost material": lambda m: m["materials"].pop(),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                made = self.made()
                mutate(made)
                result = self.run_mock_import(made)
                self.assertFalse(result["ok"], (fault, result))
                self.assertTrue(any(not c["ok"] for c in result["checks"]), result)

    def test_empty_or_stale_current_import_response_is_a_bridge_failure(self):
        cases = [dict(self.made(), imported=[]), dict(self.made(), meshes=[])]
        stale = self.made()
        stale["meshes"][0]["path"] = "/Game/OldImport/" + self.asset
        cases.append(stale)
        for made in cases:
            with self.subTest(made=made):
                with mock.patch.object(wire, "call", return_value={"result": made}) as call:
                    with self.assertRaises(wire.BridgeError):
                        saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
                call.assert_called_once()

    def test_malformed_material_evidence_cannot_claim_a_successful_import(self):
        cases = [dict(self.made(), materials=[None]), dict(self.made(), materials=[{}]),
                 dict(self.made(), materials=[{"name": "Wood", "path": ""}]),
                 dict(self.made(), materials=[{"name": "", "path": self.dest + "/M_Wood"}])]
        duplicate = self.made()
        duplicate["materials"].append(copy.deepcopy(duplicate["materials"][0]))
        cases.append(duplicate)
        invalid_slot = self.made()
        invalid_slot["meshes"][0]["materials"] = [None]
        cases.append(invalid_slot)
        for made in cases:
            with self.subTest(materials=made["materials"]):
                with mock.patch.object(wire, "call", return_value={"result": made}) as call:
                    with self.assertRaises(wire.BridgeError):
                        saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
                call.assert_called_once()

    def test_engine_parent_cannot_ship_even_when_repair_count_claims_success(self):
        made = self.made()
        made["materials"][0]["parent"] = "/InterchangeAssets/gltf/MI_Wood.MI_Wood"
        made["reparented"] = 1  # The observed parent, not an attempted repair, is the evidence.
        result = self.run_mock_import(made)
        self.assertFalse(result["ok"])
        failed = [c for c in result["checks"] if not c["ok"]]
        self.assertEqual([c["check"] for c in failed], [NANITE_CHECK])

    def test_material_parent_evidence_must_be_an_explicit_string(self):
        for parent in (None, False, 1, [], {}):
            with self.subTest(parent=parent):
                made = self.made()
                made["materials"][0]["parent"] = parent
                with mock.patch.object(wire, "call", return_value={"result": made}) as call:
                    with self.assertRaises(wire.BridgeError):
                        saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
                call.assert_called_once()
        made = self.made()
        del made["materials"][0]["parent"]
        with mock.patch.object(wire, "call", return_value={"result": made}) as call:
            with self.assertRaises(wire.BridgeError):
                saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
        call.assert_called_once()

    def test_explicit_empty_or_custom_project_parent_is_valid_material_evidence(self):
        for parent in ("", "/Game/Custom/M_Base.M_Base"):
            with self.subTest(parent=parent):
                made = self.made()
                made["materials"][0]["parent"] = parent
                result = self.run_mock_import(made)
                self.assertTrue(result["ok"], result)

    def test_closed_or_reset_bridge_retains_verified_reimport_source(self):
        for failure in (wire.BridgeError("Unreal", {"message": "bridge closed"}),
                        ConnectionResetError("connection reset"), ConnectionRefusedError("editor closed")):
            with self.subTest(failure=type(failure).__name__):
                captured = []

                def fail(addr, command, **params):
                    path = Path(import_params(params["code"])["path"])
                    self.assertTrue(path.exists())
                    captured.append(path)
                    raise failure

                with mock.patch.object(wire, "call", side_effect=fail) as call:
                    with self.assertRaises((wire.BridgeError, OSError)):
                        saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
                call.assert_called_once()
                self.assertTrue(all(p.is_file() and p.read_bytes() == self.source.read_bytes() for p in captured))

    def test_import_snapshot_is_independent_of_a_later_source_write(self):
        before = self.source.read_bytes()
        captured = []

        def bridge(addr, command, **params):
            path = Path(import_params(params["code"])["path"])
            captured.append(path)
            self.source.write_bytes(before + b"concurrent writer")
            self.assertEqual(path.read_bytes(), before)
            return {"result": self.made()}

        with mock.patch.object(wire, "call", side_effect=bridge):
            result = saved.ship_saved(str(self.job_path), handoff_root=str(self.root))
        self.assertTrue(result["ok"])
        self.assertTrue(all(p.is_file() and p.read_bytes() == before for p in captured))
        self.assertEqual(self.source.read_bytes(), before + b"concurrent writer")

    def test_matching_content_addressed_cache_is_reused_without_rewrite(self):
        first = self.run_mock_import()
        cached = Path(first["provenance"]["import_snapshot"])
        before = cached.stat().st_mtime_ns
        second = self.run_mock_import()
        self.assertEqual(first["provenance"]["import_snapshot"], second["provenance"]["import_snapshot"])
        self.assertEqual(cached.stat().st_mtime_ns, before)

    def test_wrong_existing_cache_cannot_be_overwritten_or_imported(self):
        digest = hashlib.sha1(self.source.read_bytes()).hexdigest()
        cached = self.root / "import-cache" / digest / (self.asset + ".glb")
        cached.parent.mkdir(parents=True)
        cached.write_bytes(b"a different file occupies this immutable cache")
        before = cached.read_bytes()
        self.reject_before_editor()
        self.assertEqual(cached.read_bytes(), before)

    def test_preexisting_cache_with_mutable_hardlink_alias_is_refused(self):
        digest = hashlib.sha1(self.source.read_bytes()).hexdigest()
        cached = self.root / "import-cache" / digest / (self.asset + ".glb")
        cached.parent.mkdir(parents=True)
        cached.write_bytes(self.source.read_bytes())
        real_stat = Path.stat

        def aliased_stat(path, *args, **kwargs):
            facts = real_stat(path, *args, **kwargs)
            if path == cached:
                values = list(facts)
                values[3] = 2  # OS stat evidence: two names can mutate this same blob.
                return os.stat_result(values)
            return facts

        with mock.patch.object(Path, "stat", autospec=True, side_effect=aliased_stat):
            self.reject_before_editor()
        self.assertEqual(cached.read_bytes(), self.source.read_bytes())

    def reject_report_alias(self, report):
        job_before, source_before = self.job_path.read_bytes(), self.source.read_bytes()
        with mock.patch.object(wire, "call") as call, redirect_stdout(io.StringIO()):
            result = saved.main(["--job", str(self.job_path), "--report", str(report)])
        self.assertNotEqual(result, 0)
        call.assert_not_called()
        self.assertEqual(self.job_path.read_bytes(), job_before)
        self.assertEqual(self.source.read_bytes(), source_before)

    def test_cli_report_cannot_truncate_job_source_or_cached_import_source(self):
        for target in (self.job_path, self.source):
            with self.subTest(target=target.name):
                self.reject_report_alias(target)
        result = self.run_mock_import()
        cached = Path(result["provenance"]["import_snapshot"])
        before = cached.read_bytes()
        self.reject_report_alias(cached)
        self.assertEqual(cached.read_bytes(), before)

    def test_cli_report_filesystem_alias_evidence_is_refused(self):
        alias = Path(self.temp.name) / "report-alias.json"
        alias.write_bytes(b"retain this independent output")
        before = alias.read_bytes()
        real_samefile, real_resolve = Path.samefile, Path.resolve

        def same_identity(path, other):
            if path == alias and Path(other) == self.source:
                return True  # OS identity evidence for a hardlink, without creating one.
            return real_samefile(path, other)

        with mock.patch.object(Path, "samefile", autospec=True, side_effect=same_identity):
            self.reject_report_alias(alias)

        def redirected(path, *args, **kwargs):
            if path == alias:
                return self.job_path  # Path-resolution evidence for a symlink, without creating one.
            return real_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", autospec=True, side_effect=redirected):
            self.reject_report_alias(alias)
        self.assertEqual(alias.read_bytes(), before)

    @unittest.skipUnless(os.environ.get("SAVED_GLB_TEST_LINKS") == "1",
                         "real hardlink creation requires explicit SAVED_GLB_TEST_LINKS=1")
    def test_cli_report_hardlink_alias_cannot_truncate_source(self):
        alias = Path(self.temp.name) / "report-hardlink.json"
        try:
            os.link(self.source, alias)
        except OSError as error:
            self.skipTest("host cannot create hardlinks: " + str(error))
        self.reject_report_alias(alias)

    @unittest.skipUnless(os.environ.get("SAVED_GLB_TEST_LINKS") == "1",
                         "real symlink creation requires explicit SAVED_GLB_TEST_LINKS=1")
    def test_cli_report_symlink_alias_cannot_truncate_job(self):
        alias = Path(self.temp.name) / "report-symlink.json"
        try:
            alias.symlink_to(self.job_path)
        except OSError as error:
            self.skipTest("host cannot create symlinks: " + str(error))
        self.reject_report_alias(alias)


class StrictImportScriptTests(Fixture):
    def fake_unreal(self, *, playing=False, empty=True):
        calls = {"tasks": 0, "imports": 0, "list_assets": 0, "task_properties": [],
                 "loads": [], "duplicates": [], "flags": [], "parents": [],
                 "recompiles": [], "save_assets": [], "save_directories": []}
        stale_path = self.dest + "/" + self.asset
        ours = "/Game/Daedalus/Materials/Gltf"

        class Material:
            def __init__(self, path, name):
                self.path, self.name = path, name
            def get_name(self): return self.name
            def get_path_name(self): return self.path
            def set_editor_property(self, key, value): calls["flags"].append((self.path, key, value))

        class Instance(Material):
            def __init__(self, path, name, parent=None):
                super().__init__(path, name)
                self.parent = parent
                self.parameters = {"base_colour": [0.7, 0.4, 0.2], "roughness": 0.8}
            def get_editor_property(self, key):
                if key == "parent": return self.parent
                raise AttributeError(key)

        base = Material("/InterchangeAssets/gltf/M_Default.M_Default", "M_Default")
        engine_parent = Instance("/InterchangeAssets/gltf/MI_Wood.MI_Wood", "MI_Wood", base)
        material = Instance(self.dest + "/M_Wood.M_Wood", "Wood", engine_parent)
        old_path = "/Game/Daedalus/Art/Old/M_Old.M_Old"
        old_material = Instance(old_path, "M_Old", engine_parent)
        calls["material"], calls["old_material"] = material, old_material

        class Slot:
            def get_editor_property(self, key):
                return {"material_slot_name": "Wood", "material_interface": material}[key]

        class Mesh:
            def get_name(self): return "Tool_Contract"
            def get_bounding_box(self):
                return types.SimpleNamespace(min=types.SimpleNamespace(x=0, y=0, z=0),
                                             max=types.SimpleNamespace(x=90, y=30, z=10))
            def get_num_triangles(self, lod): return 2
            def get_static_mesh_description(self, lod):
                return types.SimpleNamespace(get_triangle_count=lambda: 2)
            def get_editor_property(self, key):
                if key == "static_materials": return [Slot()]
                raise AttributeError(key)

        class Task:
            def __init__(self):
                calls["tasks"] += 1
                self.properties = {}
            def set_editor_property(self, key, value): self.properties[key] = value
            def get_editor_property(self, key):
                if key == "imported_object_paths": return [] if empty else [stale_path]
                return self.properties.get(key)

        mesh = Mesh()
        assets = {stale_path: mesh, base.path.split(".")[0]: base,
                  engine_parent.path.split(".")[0]: engine_parent,
                  material.path.split(".")[0]: material, old_path.split(".")[0]: old_material}
        def import_tasks(tasks):
            calls["imports"] += 1
            calls["task_properties"].extend(copy.deepcopy(task.properties) for task in tasks)
        def list_assets(*args, **kwargs):
            calls["list_assets"] += 1
            return [stale_path]
        def load_asset(path):
            calls["loads"].append(path)
            return assets.get(path.split(".")[0])
        def duplicate_asset(source, destination):
            calls["duplicates"].append((source, destination))
            original = assets[source]
            name = destination.rsplit("/", 1)[-1]
            duplicate = (Instance(destination + "." + name, name, original.parent)
                         if isinstance(original, Instance) else Material(destination + "." + name, name))
            assets[destination] = duplicate
            return duplicate
        def set_parent(instance, parent):
            calls["parents"].append((instance.path, parent.path))
            instance.parent = parent

        module = types.ModuleType("unreal")
        module.UnrealEditorSubsystem = object
        module.get_editor_subsystem = lambda cls: types.SimpleNamespace(
            get_game_world=lambda: object() if playing else None)
        module.AssetImportTask = Task
        module.AssetToolsHelpers = types.SimpleNamespace(
            get_asset_tools=lambda: types.SimpleNamespace(import_asset_tasks=import_tasks))
        module.EditorAssetLibrary = types.SimpleNamespace(
            list_assets=list_assets, load_asset=load_asset,
            does_asset_exist=lambda path: path in assets, duplicate_asset=duplicate_asset,
            save_asset=lambda path, **kw: calls["save_assets"].append((path, kw)),
            save_directory=lambda path, **kw: calls["save_directories"].append((path, kw)))
        module.MaterialEditingLibrary = types.SimpleNamespace(
            recompile_material=lambda asset: calls["recompiles"].append(asset.path),
            set_material_instance_parent=set_parent)
        module.StaticMesh, module.MaterialInterface, module.MaterialInstanceConstant = Mesh, Material, Instance
        calls["ours"] = ours
        return module, calls

    def execute_import(self, unreal_module, *, save=True):
        code = sides.script(saved.STRICT_UNREAL_IMPORT, path=str(self.source), dest=self.dest, save=save)
        scope = {}
        with mock.patch.dict(sys.modules, {"unreal": unreal_module}):
            exec(compile(code, "saved-import-contract", "exec"), scope)
        return scope.get("result")

    def test_play_prevents_asset_import_inside_the_same_editor_call(self):
        module, calls = self.fake_unreal(playing=True)
        with self.assertRaisesRegex(RuntimeError, "[Pp]lay"):
            self.execute_import(module)
        self.assertEqual(calls["tasks"], 0)
        self.assertEqual(calls["imports"], 0)
        self.assertEqual(calls["list_assets"], 0)

    def test_empty_current_import_cannot_claim_a_matching_stale_destination_mesh(self):
        module, calls = self.fake_unreal()
        with self.assertRaises(RuntimeError):
            self.execute_import(module)
        self.assertEqual(calls["imports"], 1)
        self.assertEqual(calls["list_assets"], 0, "old assets must not disguise an empty import")

    def test_current_material_repair_flags_and_destination_save_are_preserved(self):
        module, calls = self.fake_unreal(empty=False)
        parameters = copy.deepcopy(calls["material"].parameters)
        old_parent = calls["old_material"].parent
        result = self.execute_import(module)
        ours = calls["ours"]
        self.assertEqual(result["reparented"], 1)
        self.assertEqual(result["materials"][0]["parent"], ours + "/MI_Wood.MI_Wood")
        self.assertEqual(calls["material"].parameters, parameters)
        self.assertEqual(calls["duplicates"], [
            ("/InterchangeAssets/gltf/M_Default", ours + "/M_Default"),
            ("/InterchangeAssets/gltf/MI_Wood", ours + "/MI_Wood")])
        self.assertEqual(calls["flags"], [
            (ours + "/M_Default.M_Default", "used_with_nanite", True),
            (ours + "/M_Default.M_Default", "used_with_instanced_static_meshes", True)])
        self.assertEqual(calls["recompiles"], [ours + "/M_Default.M_Default"])
        self.assertEqual(calls["save_assets"], [
            (ours + "/M_Default", {"only_if_is_dirty": False}),
            (ours + "/MI_Wood", {"only_if_is_dirty": False})])
        self.assertEqual(calls["save_directories"], [
            (self.dest, {"only_if_is_dirty": True, "recursive": True})])
        self.assertEqual(calls["task_properties"], [{
            "filename": str(self.source), "destination_path": self.dest,
            "automated": True, "replace_existing": True, "save": True}])
        self.assertEqual(calls["list_assets"], 0, "new imports must not scan or migrate old library assets")
        self.assertNotIn(calls["old_material"].path, calls["loads"])
        self.assertIs(calls["old_material"].parent, old_parent)

    def test_no_save_skips_destination_save_but_keeps_project_base_repair(self):
        module, calls = self.fake_unreal(empty=False)
        result = self.execute_import(module, save=False)
        self.assertEqual(result["reparented"], 1)
        self.assertEqual(calls["save_directories"], [])
        self.assertEqual(len(calls["save_assets"]), 2)
        self.assertFalse(calls["task_properties"][0]["save"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
