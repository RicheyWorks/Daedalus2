# SPDX-License-Identifier: MIT
"""Synthetic-only contract and failure checks for the offline exporter."""

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools.campaign_throughput_toolkit.catalog import (
    CatalogError, CatalogExporter, MAX_RECEIPT_BYTES, R18_ROOT,
    active_item, csv_bytes, immutable,
)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / "offline"

    def receipt(self, chunk=1, *, kind="skull", name='Synthetic, "Only" 雪'):
        identity = ("SK" if kind == "skull" else "TT") + f"{chunk:03d}_Synthetic"
        blend = self.base / (identity + ".blend")
        blend.write_bytes(b"synthetic blend fixture only")
        fbx = self.base / (identity + ".fbx")
        fbx.write_bytes(b"synthetic fbx fixture only")
        source = {
            "id": identity, "name": name, "kind": kind, "index": chunk,
            "expansion_wave": chunk,
            "blend": self.pin(blend),
            "source_units": "Metres", "lineage": "Synthetic fixture",
            "parts": [{"group": "Head", "fbx": self.pin(fbx),
                       "render_triangles": 12, "materials": ["Gold"]}],
        }
        row = {
            "id": identity, "name": name, "kind": kind, "index": chunk,
            "source": source, "catalog_identity": identity, "native_saved": True,
            "native_admission": "Valid", "imports": [{
                "asset": f"{R18_ROOT}/R18_C{chunk:04d}/Items/{identity}/Mesh.Mesh",
                "source": copy.deepcopy(source["parts"][0]),
                "slots": [{"native": f"{R18_ROOT}/R18_C{chunk:04d}/Gold.Gold"}],
            }],
        }
        native = {
            "world": f"{R18_ROOT}/R18_C{chunk:04d}/L_GrandCollection_C{chunk:04d}.L_GrandCollection_C{chunk:04d}",
            "saved": True,
            "item_records": {identity: row}, "native_valid_parts": 1,
        }
        path = self.base / f"receipt-{chunk}.json"
        path.write_text(json.dumps({"native": native}), encoding="utf-8")
        return native, path

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}

    def test_csv_exact_legacy_columns_encoding_and_order(self):
        native, _ = self.receipt()
        second, _ = self.receipt(2, kind="toter", name="Second")
        native["item_records"].update(second["item_records"])
        # Literal established contract, including quoting, Unicode and CRLF.
        legacy_columns = ["name", "kind", "category", "world", "owner", "status",
                          "queue_status", "blender_files", "uassets", "path"]
        expected = io.StringIO(newline="")
        writer = csv.DictWriter(expected, fieldnames=legacy_columns)
        writer.writeheader()
        for identity, item in native["item_records"].items():
            writer.writerow(dict(zip(legacy_columns, [
                identity + " " + item["name"], "Prop",
                "living_trash_art" if item["kind"] == "toter" else "skull_sculpture",
                "DaedalusDiscovery", "project", "native_saved_sandbox", "REVIEW",
                item["source"]["blend"]["path"],
                ";".join(part["asset"] for part in item["imports"]),
                native["world"].split(".")[0],
            ])))
        actual = csv_bytes(native)
        self.assertEqual(actual, expected.getvalue().encode("utf-8"))
        self.assertTrue(actual.endswith(b"\r\n"))
        self.assertFalse(actual.startswith(b"\xef\xbb\xbf"))
        self.assertLess(actual.index(b"SK001"), actual.index(b"TT002"))

    def test_incremental_append_no_global_snapshot_and_reuse(self):
        _, path = self.receipt()
        with CatalogExporter(self.output, trust_metadata=True) as exporter:
            first = exporter.export_chunk(self.pin(path), 1)
            self.assertEqual(first["new_item_records"], 1)
            current = self.output / "current.json"
            stamp = current.stat().st_mtime_ns
            before = current.read_bytes()
            again = exporter.export_chunk(self.pin(path), 1)
            self.assertTrue(again["metadata_cache_reused"])
            self.assertEqual(again["receipt_bytes_hashed"], 0)
            self.assertEqual(current.stat().st_mtime_ns, stamp)
            self.assertEqual(current.read_bytes(), before)
            _, next_path = self.receipt(2, kind="toter")
            second = exporter.export_chunk(self.pin(next_path), 2)
            self.assertEqual(second["new_item_records"], 1)
            snapshot = exporter.snapshot()
            self.assertEqual(snapshot["item_records"], 2)
            self.assertFalse(second["global_snapshot_rewritten"])
            self.assertFalse(second["native_acceptance_performed"])

    def test_changed_receipt_only_timing_no_pointer_or_csv_rewrite(self):
        native, path = self.receipt()
        with CatalogExporter(self.output) as exporter:
            exporter.export_chunk(self.pin(path), 1)
            output_names = ["current.json", "Chunk0001.catalog-staging.csv",
                            "Chunk0001.items-delta.json"]
            previous = {name: (self.output / name).stat().st_mtime_ns for name in output_names}
            path.write_text(json.dumps({"native": native, "elapsed_seconds": 123}), encoding="utf-8")
            result = exporter.export_chunk(self.pin(path), 1)
            self.assertTrue(result["reused_unchanged_export"])
            self.assertFalse(result["metadata_cache_reused"])
            self.assertEqual(previous, {name: (self.output / name).stat().st_mtime_ns
                                        for name in output_names})

    def test_identity_assembly_and_count_collisions_refused(self):
        native, path = self.receipt()
        with CatalogExporter(self.output) as exporter:
            exporter.export_chunk(self.pin(path), 1)
            identity = next(iter(native["item_records"]))
            native["item_records"][identity]["source"]["lineage"] = "changed immutable source"
            path.write_text(json.dumps({"native": native}), encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "Append-only"):
                exporter.export_chunk(self.pin(path), 1)
            native["item_records"][identity]["catalog_identity"] = "another ID"
            path.write_text(json.dumps({"native": native}), encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "identity mismatch"):
                exporter.export_chunk(self.pin(path), 1)

    def test_hash_pin_duplicate_json_and_corrupt_output_refused(self):
        _, path = self.receipt()
        pinned = self.pin(path)
        path.write_bytes(path.read_bytes() + b" ")
        with CatalogExporter(self.output) as exporter:
            with self.assertRaisesRegex(CatalogError, "explicit pin"):
                exporter.export_chunk(pinned, 1)
            exporter.export_chunk(self.pin(path), 1)
            (self.output / "Chunk0001.catalog-staging.csv").write_bytes(b"corrupt")
            with self.assertRaisesRegex(CatalogError, "Published chunk changed"):
                exporter.export_chunk(self.pin(path), 1)
        duplicate = self.base / "duplicate.json"
        duplicate.write_bytes(b'{"saved":true,"saved":true}')
        with CatalogExporter(self.base / "other") as exporter:
            with self.assertRaisesRegex(CatalogError, "Duplicate JSON"):
                exporter.export_chunk(self.pin(duplicate), 1)

    def test_pending_publication_refuses_replay(self):
        _, path = self.receipt()
        with CatalogExporter(self.output) as exporter:
            with mock.patch("tools.campaign_throughput_toolkit.catalog._exclusive",
                            wraps=__import__("tools.campaign_throughput_toolkit.catalog",
                                             fromlist=["_exclusive"])._exclusive) as write:
                original = write._mock_wraps

                def fail_delta(target, raw):
                    if target.name.endswith("items-delta.json"):
                        raise OSError("synthetic disk failure")
                    return original(target, raw)

                write.side_effect = fail_delta
                with self.assertRaisesRegex(OSError, "synthetic disk"):
                    exporter.export_chunk(self.pin(path), 1)
        self.assertTrue((self.output / "pending.json").exists())
        self.assertFalse((self.output / "current.json").exists())
        with self.assertRaisesRegex(CatalogError, "Uncertain pending"):
            CatalogExporter(self.output)

    def test_snapshot_immutable_and_existing_unrecognized_output_refused(self):
        existing = self.base / "existing"
        existing.mkdir()
        with self.assertRaisesRegex(CatalogError, "exact offline"):
            CatalogExporter(existing)
        _, path = self.receipt()
        with CatalogExporter(self.output) as exporter:
            exporter.export_chunk(self.pin(path), 1)
            exporter.snapshot()
            _, second = self.receipt(2)
            exporter.export_chunk(self.pin(second), 2)
            with self.assertRaisesRegex(CatalogError, "Existing snapshot differs"):
                exporter.snapshot()
            self.assertEqual(exporter.snapshot("stop-two.json")["item_records"], 2)

    def test_adapter_preserves_ids_and_immutable_field_contract(self):
        native, path = self.receipt()
        identity, row = next(iter(native["item_records"].items()))
        item = active_item(identity, row, native["world"], self.pin(path))
        self.assertEqual(item["stable_item_id"], identity)
        self.assertEqual(item["assembly"]["parts"][0]["asset_path"], row["imports"][0]["asset"])
        copied = copy.deepcopy(item)
        copied["status"]["headwear_motion"] = "mutable receipt status"
        self.assertEqual(immutable(item), immutable(copied))
        copied["assembly"]["world"] = "/Game/Other"
        self.assertNotEqual(immutable(item), immutable(copied))

    def test_full_checkpoint_rejects_corrupt_cached_payload(self):
        _, path = self.receipt()
        with CatalogExporter(self.output) as exporter:
            exporter.export_chunk(self.pin(path), 1)
            row = exporter.db.execute("SELECT identity,payload FROM items").fetchone()
            payload = json.loads(row[1])
            payload["name"] = "corrupt cached presentation field"
            with exporter.db:
                exporter.db.execute("UPDATE items SET payload=? WHERE identity=?",
                                    (json.dumps(payload), row[0]))
            with self.assertRaisesRegex(CatalogError, "Lookup cache differs"):
                exporter.export_chunk(self.pin(path), 1, full=True)
            with self.assertRaisesRegex(CatalogError, "Lookup cache differs"):
                exporter.snapshot()

    def test_source_import_ordered_bijection_and_typed_parts(self):
        native, path = self.receipt()
        identity = next(iter(native["item_records"]))
        row = native["item_records"][identity]
        second = copy.deepcopy(row["source"]["parts"][0])
        second["group"] = "Headwear"
        second["fbx"]["path"] += ".second"
        row["source"]["parts"].append(second)
        second_import = copy.deepcopy(row["imports"][0])
        second_import["source"] = copy.deepcopy(second)
        second_import["asset"] = second_import["asset"].replace("Mesh.Mesh", "Hat.Hat")
        row["imports"].append(second_import)
        cases = {}
        missing = copy.deepcopy(native)
        missing["item_records"][identity]["imports"].pop()
        cases["missing"] = missing
        duplicate = copy.deepcopy(native)
        duplicate["item_records"][identity]["imports"][1]["source"] = copy.deepcopy(row["source"]["parts"][0])
        cases["duplicate"] = duplicate
        reordered = copy.deepcopy(native)
        reordered["item_records"][identity]["imports"].reverse()
        cases["reordered"] = reordered
        malformed = copy.deepcopy(native)
        malformed["item_records"][identity]["imports"][0] = "invalid part"
        cases["malformed"] = malformed
        slot = copy.deepcopy(native)
        slot["item_records"][identity]["imports"][0]["slots"] = [None]
        cases["malformed-slot"] = slot
        for key, value in cases.items():
            with self.subTest(key=key), CatalogExporter(self.base / ("output-" + key)) as exporter:
                path.write_text(json.dumps({"native": value}), encoding="utf-8")
                with self.assertRaises(CatalogError):
                    exporter.export_chunk(self.pin(path), 1)
                self.assertFalse((exporter.root / "current.json").exists())

    def test_chunk_world_source_wave_must_match(self):
        native, path = self.receipt()
        identity = next(iter(native["item_records"]))
        cases = []
        wrong_world = copy.deepcopy(native)
        wrong_world["world"] = wrong_world["world"].replace("C0001", "C0002")
        cases.append(wrong_world)
        wrong_object = copy.deepcopy(native)
        wrong_object["world"] += ".Other"
        cases.append(wrong_object)
        wrong_wave = copy.deepcopy(native)
        wrong_wave["item_records"][identity]["source"]["expansion_wave"] = 2
        cases.append(wrong_wave)
        wrong_type = copy.deepcopy(native)
        wrong_type["item_records"][identity]["source"]["expansion_wave"] = True
        cases.append(wrong_type)
        for index, value in enumerate(cases):
            with self.subTest(case=index), CatalogExporter(self.base / f"bad-chunk-{index}") as exporter:
                path.write_text(json.dumps({"native": value}), encoding="utf-8")
                with self.assertRaisesRegex(CatalogError, "mismatch"):
                    exporter.export_chunk(self.pin(path), 1)
        # Package-only world paths are also emitted by the retained producer.
        native["world"] = native["world"].split(".")[0]
        path.write_text(json.dumps({"native": native}), encoding="utf-8")
        with CatalogExporter(self.output) as exporter:
            exporter.export_chunk(self.pin(path), 1)

    def test_nonfinite_json_and_receipt_size_bound_before_read(self):
        native, path = self.receipt()
        for index, number in enumerate(("NaN", "Infinity", "-Infinity", "1e999")):
            raw = json.dumps({"native": native})[:-1] + ', "timing":' + number + "}"
            path.write_text(raw, encoding="utf-8")
            with self.subTest(number=number), CatalogExporter(self.base / f"nonfinite-{index}") as exporter:
                with self.assertRaisesRegex(CatalogError, "Non-finite JSON"):
                    exporter.export_chunk(self.pin(path), 1)
        with CatalogExporter(self.output) as exporter:
            oversized = {"path": str(path), "bytes": MAX_RECEIPT_BYTES + 1, "sha256": "0" * 64}
            with mock.patch("tools.campaign_throughput_toolkit.catalog._read_stable") as read:
                with self.assertRaisesRegex(CatalogError, "byte bound"):
                    exporter.export_chunk(oversized, 1)
                read.assert_not_called()

    def test_retained_lock_refuses_constructor_reuse_and_cache_update(self):
        native, path = self.receipt()
        with CatalogExporter(self.output, trust_metadata=True) as exporter:
            exporter.export_chunk(self.pin(path), 1)
            lock = self.output / "writer.lock"
            lock.write_bytes(b"foreign owner retained lock")
            for changed in (False, True):
                if changed:
                    path.write_text(json.dumps({"native": native, "timing": 2}), encoding="utf-8")
                with self.subTest(changed=changed), self.assertRaisesRegex(CatalogError, "writer lock"):
                    exporter.export_chunk(self.pin(path), 1)
                self.assertEqual(lock.read_bytes(), b"foreign owner retained lock")
            with self.assertRaisesRegex(CatalogError, "writer lock"):
                exporter.snapshot()
            with self.assertRaisesRegex(CatalogError, "writer lock"):
                CatalogExporter(self.output, trust_metadata=True)


if __name__ == "__main__":
    unittest.main()
