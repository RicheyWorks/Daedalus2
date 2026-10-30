# SPDX-License-Identifier: MIT
"""Synthetic retained receipts only; never reads campaign data or imports Unreal."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.unreal_mcp import native_validation_snapshot_consumer as consumer
from .evidence import EvidenceError, decode, read_pinned
from .validation import validate_chunk


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def snapshot(paths):
    flags = {key: True for key in consumer.SETTINGS_BOOL_KEYS}
    flags.update(ValidationUsecase="EDataValidationUsecase::Script", MaxAssetsToValidate=len(paths) + 1)
    counts = {key: 0 for key in consumer.COUNT_KEYS}
    counts.update(NumRequested=len(paths), NumChecked=len(paths), NumValid=len(paths))
    counts.update(bAssetLimitReached=False, ValidatorMessages=[], AssetsDetails={
        p: {"PackageName": p.split(".")[0], "AssetName": p.split(".")[1], "Result": "Valid",
            "ValidationErrors": [], "ValidationWarnings": [], "ValidationMessages": [], "ExternalObjects": []}
        for p in paths})
    return json.dumps({"snapshot_kind": consumer.SNAPSHOT_KIND, "requested_assets": paths,
                       "native_return": 0, "results": counts, "settings": flags,
                       "provenance": {"fresh_out_results": "synthetic", "native_invocation": "synthetic",
                                      "captured_at_utc": "synthetic"},
                       "native_runtime_qualified": False, "unknowns": ["synthetic_fixture_only"]})


def fixture(root):
    source, records, paths = [], {}, []
    namespace = "/Game/Daedalus/Sandbox/NativeDiscovery/20261024/R18_C0001"
    for kind in ("skull", "toter"):
        for index in range(101, 111):
            identity = ("SK" if kind == "skull" else "TT") + str(index) + "_Synthetic"
            blend, fbx = root / (identity + ".blend"), root / (identity + ".fbx")
            blend.write_bytes(("synthetic blend " + identity).encode())
            fbx.write_bytes(("synthetic fbx " + identity).encode())
            part = {"group": "Body", "name": identity + "_Body", "fbx": pin(fbx), "render_triangles": 12,
                    "dimensions_m": [1, 2, 3], "material_slots": 1, "materials": ["Synthetic"]}
            item = {"id": identity, "kind": kind, "index": index, "name": "Synthetic",
                    "source_created": True, "blend": pin(blend), "parts": [part]}
            asset = namespace + "/Items/" + identity + "/Parts/Body/" + part["name"] + "." + part["name"]
            material = namespace + "/Items/" + identity + "/MI_Body.MI_Body"
            source.append(item)
            records[identity] = {"id": identity, "catalog_identity": identity, "kind": kind, "index": index,
                                 "name": item["name"], "source": copy.deepcopy(item), "native_saved": True,
                                 "native_admission": "Valid", "imports": [{"asset": asset, "source": part,
                                     "dimensions_cm": [100, 200, 300], "triangles": 12, "saved": True,
                                     "slots": [{"source_slot": "Synthetic", "native": material}]}]}
            paths.append(asset)
    groups = [{"paths": paths[n:n + 16], "report": {"status": "Valid", "native_invoked": True,
               "accepted": True, "native_return": 0, "cancellation_observed": False,
               "snapshot_json": snapshot(paths[n:n + 16])}} for n in range(0, len(paths), 16)]
    manifest = {"chunk": 1, "range": [101, 110], "counts": {"skull": 10, "toter": 10},
                "held": [], "items": source}
    native = {"saved": True, "world": namespace + "/L_GrandCollection_C0001.L_GrandCollection_C0001",
              "dirty": {"maps": [], "content": []}, "play": False, "import_active": False,
              "item_records": records, "native_valid_parts": 20, "admission": groups, "assets": []}
    return manifest, {"native": native}


class RetainedValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest, self.receipt = fixture(self.root)

    def run_validation(self):
        source_path, receipt_path = self.root / "source.json", self.root / "native.json"
        source_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        return validate_chunk(pin(source_path), pin(receipt_path), roots=[self.root], expected_chunk=1,
                              expected_range=[101, 110], expected_ids=[r["id"] for r in self.manifest["items"]])

    def test_proposal_is_explicit_offline_and_covers_new_references_once(self):
        report = self.run_validation()
        self.assertFalse(report["native_admission"])
        self.assertFalse(report["native_invoked"])
        self.assertEqual(report["files_rehashed"], 42)
        batches = report["proposal"]["batches"]
        flattened = [p for group in batches for p in group]
        self.assertEqual(len(flattened), 40)
        self.assertEqual(len(set(flattened)), 40)
        self.assertTrue(all(len(group) <= 16 for group in batches))
        self.assertEqual(len(report["proposal"]["unvalidated_new_references"]), 20)

    def test_identity_count_source_and_native_mismatches_refused(self):
        for mutate in (
            lambda: self.manifest.update(counts={"skull": 9, "toter": 10}),
            lambda: self.manifest.update(range=[102, 111]),
            lambda: self.receipt["native"]["item_records"].pop(next(iter(self.receipt["native"]["item_records"]))),
            lambda: next(iter(self.receipt["native"]["item_records"].values())).update(catalog_identity="Changed"),
            lambda: next(iter(self.receipt["native"]["item_records"].values()))["source"].update(name="Changed"),
        ):
            self.manifest, self.receipt = fixture(self.root)
            mutate()
            with self.assertRaises(EvidenceError):
                self.run_validation()

    def test_flipped_source_bytes_refused(self):
        Path(self.manifest["items"][0]["parts"][0]["fbx"]["path"]).write_bytes(b"flipped")
        with self.assertRaisesRegex(EvidenceError, "byte count|hash"):
            self.run_validation()

    def test_geometry_delta_requires_exact_retained_source_proof(self):
        part = next(iter(self.receipt["native"]["item_records"].values()))["imports"][0]
        part["triangles"] = 11
        with self.assertRaisesRegex(EvidenceError, "geometry mismatch"):
            self.run_validation()
        part["source_render_evidence"] = {"build_settings_changed": False, "source_triangles": 12,
                                         "source_retained": 12, "queried_triangle_coverage": 12,
                                         "render_triangles": 11, "zero_area_source_triangles": 1,
                                         "native_copy_outcome": "GeometryScriptOutcomePins.SUCCESS"}
        self.assertEqual(self.run_validation()["status"], "retained_evidence_consistent")

    def test_retained_save_admission_material_and_copy_outcomes_refused(self):
        for field, value in (("native_admission", "Held"), ("saved", False),
                             ("source_slot", "UnknownMaterial"), ("native_copy_outcome", "FAILURE")):
            self.manifest, self.receipt = fixture(self.root)
            row = next(iter(self.receipt["native"]["item_records"].values()))
            part = row["imports"][0]
            if field == "native_admission":
                row[field] = value
            elif field == "source_slot":
                part["slots"][0][field] = value
            elif field == "native_copy_outcome":
                part["triangles"] = 11
                part["source_render_evidence"] = {"build_settings_changed": False, "source_triangles": 12,
                    "source_retained": 12, "queried_triangle_coverage": 12, "render_triangles": 11,
                    "zero_area_source_triangles": 1, field: value}
            else:
                part[field] = value
            with self.assertRaises(EvidenceError):
                self.run_validation()

    def test_snapshot_detail_package_alias_refused(self):
        report = self.receipt["native"]["admission"][0]["report"]
        document = json.loads(report["snapshot_json"])
        detail = next(iter(document["results"]["AssetsDetails"].values()))
        detail.update(PackageName="/Game/Other", AssetName="Other")
        report["snapshot_json"] = json.dumps(document)
        with self.assertRaisesRegex(EvidenceError, "detail/settings identity"):
            self.run_validation()

    def test_cross_item_import_swap_refused(self):
        first, second = list(self.receipt["native"]["item_records"].values())[:2]
        first["imports"][0]["asset"], second["imports"][0]["asset"] = (
            second["imports"][0]["asset"], first["imports"][0]["asset"])
        with self.assertRaisesRegex(EvidenceError, "imported asset"):
            self.run_validation()

    def test_native_envelope_and_canonical_snapshot_cannot_fake_coverage(self):
        group = self.receipt["native"]["admission"][0]
        group["report"]["accepted"] = False
        with self.assertRaisesRegex(EvidenceError, "envelope held"):
            self.run_validation()
        group["report"]["accepted"] = True
        group["report"]["snapshot_json"] = snapshot(group["paths"][:-1])
        with self.assertRaisesRegex(EvidenceError, "snapshot identity"):
            self.run_validation()

    def test_duplicate_json_and_traversal_refused(self):
        with self.assertRaisesRegex(EvidenceError, "duplicate"):
            decode('{"native":{},"native":{}}')
        for number in ("NaN", "Infinity", "1e999"):
            with self.assertRaisesRegex(EvidenceError, "nonfinite"):
                decode('{"value":' + number + '}')
        path = self.root / "file"
        path.write_bytes(b"fixture")
        retained = pin(path)
        retained["path"] = str(self.root / ".." / self.root.name / "file")
        with self.assertRaisesRegex(EvidenceError, "traversal"):
            read_pinned(retained, [self.root])


if __name__ == "__main__":
    unittest.main()
