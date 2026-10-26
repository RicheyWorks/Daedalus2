# SPDX-License-Identifier: MIT
"""Independent diagnostics contract regressions; synthetic data, no live readers.

Run with: python -m unittest discover -s tools/pc -p test_diagnostics_provider_regressions.py
"""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostics as d  # noqa: E402


NOW = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
STAMP = "2024-01-02T12:00:00Z"
METRICS = {"cpu_pct": 0, "physical_available_bytes": 0}
SYSTEM_METRICS = {"physical_total_bytes": 1024, "physical_available_bytes": 0,
                  "committed_bytes": 0, "commit_limit_bytes": 4096, "ram_pct": 100}


def sample(metrics=None, **changes):
    args = {"provenance": "live", "sampled_at": NOW, "observed_at": NOW}
    args.update(changes)
    return d.snapshot("synthetic_provider", METRICS if metrics is None else metrics, **args)


def vitals(**changes):
    value = {"when": STAMP, "total_mb": 1000, "free_mb": 400, "cpu_pct": 0,
             "gpu": "0, 0, 1024, 20", "editor_mb": 999,
             "top": [{"Id": 101, "ProcessName": "UnrealEditor_Synthetic", "mb": 0, "cpu_s": 250}]}
    value.update(changes)
    return value


class SnapshotRegressions(unittest.TestCase):
    def assert_no_values(self, result):
        self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))

    def test_zero_is_current_and_has_fixed_units(self):
        result = sample()
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["freshness"], "current")
        self.assertEqual(result["metrics"]["cpu_pct"], {"value": 0, "unit": "percent", "status": "current"})
        self.assertEqual(result["metrics"]["physical_available_bytes"], {"value": 0, "unit": "bytes", "status": "current"})

    def test_missing_and_null_metrics_are_not_zero(self):
        for inputs in ({}, {"cpu_pct": None}):
            with self.subTest(inputs=inputs):
                result = sample(inputs)
                self.assert_no_values(result)
                self.assertEqual(result["metrics"]["cpu_pct"]["status"], "missing")

    def test_invalid_metric_types_ranges_and_nonfinite_are_null(self):
        for value in (True, False, -1, 101, float("nan"), float("inf"), -float("inf"), "0", [], {}):
            with self.subTest(value=repr(value)):
                result = sample({"cpu_pct": value})
                self.assertEqual(result["metrics"]["cpu_pct"], {"value": None, "unit": "percent", "status": "invalid"})
                json.dumps(result, allow_nan=False)
        self.assertEqual(sample({"physical_total_bytes": -1})["metrics"]["physical_total_bytes"]["status"], "invalid")
        self.assertEqual(sample({"cpu_pct": 100})["metrics"]["cpu_pct"]["value"], 100)

    def test_unrecognized_metrics_are_not_exported(self):
        result = sample({"cpu_pct": 0, "synthetic_private_export": "do-not-copy"})
        self.assertNotIn("synthetic_private_export", json.dumps(result))
        self.assertNotIn("do-not-copy", json.dumps(result))

    def test_freshness_deadline_and_stale_values_are_independent_of_read_time(self):
        for age, status in ((0, "current"), (29.999999, "current"), (30, "stale"), (31, "stale"), (3600, "stale")):
            with self.subTest(age=age):
                result = sample(sampled_at=NOW - timedelta(seconds=age), max_age_seconds=30)
                self.assertEqual(result["freshness"], status)
                self.assertEqual(result["age_seconds"], age)
                if status == "stale":
                    self.assert_no_values(result)
                    self.assertEqual(result["metrics"]["cpu_pct"]["status"], "stale")

    def test_equivalent_offsets_are_normalized_to_utc(self):
        result = sample(sampled_at="2024-01-02T13:00:00+01:00", observed_at=STAMP)
        self.assertEqual(result["freshness"], "current")
        self.assertEqual(result["age_seconds"], 0)
        self.assertEqual(result["sampled_at"], "2024-01-02T12:00:00.000000Z")

    def test_missing_naive_invalid_and_future_source_times_are_unknown(self):
        for stamp in (None, NOW.replace(tzinfo=None), "2024-01-02T12:00:00", "not-a-time", True, 1, [], NOW + timedelta(microseconds=1)):
            with self.subTest(stamp=repr(stamp)):
                result = sample(sampled_at=stamp)
                self.assertEqual(result["freshness"], "unknown")
                self.assertEqual(result["age_seconds"], None)
                self.assert_no_values(result)

    def test_invalid_observation_time_is_refused(self):
        for stamp in (None, NOW.replace(tzinfo=None), "2024-01-02T12:00:00", "bad", True, 1):
            with self.subTest(stamp=repr(stamp)):
                with self.assertRaises(ValueError):
                    sample(observed_at=stamp)

    def test_provider_availability_is_separate_from_freshness(self):
        for state in ("unavailable", "unsupported", "failed"):
            with self.subTest(state=state):
                result = sample(availability=state, reason="synthetic_reason")
                self.assertEqual(result["availability"], state)
                self.assertEqual(result["reason"], "synthetic_reason")
                self.assertEqual(result["freshness"], "unavailable")
                self.assert_no_values(result)
                self.assertNotEqual(result["metrics"]["cpu_pct"]["status"], "current")

    def test_invalid_enums_and_freshness_budget_are_refused(self):
        for changes in ({"availability": "minimized"}, {"provenance": "tmog"}, {"provenance": "os_fallback"},
                        {"availability": []}, {"availability": {}}, {"provenance": None},
                        {"provenance": []}, {"max_age_seconds": 0}, {"max_age_seconds": -1}, {"max_age_seconds": True},
                        {"max_age_seconds": float("nan")}, {"max_age_seconds": float("inf")}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    sample(**changes)

    def test_process_restart_with_same_pid_invalidates_old_measurements(self):
        expected = {"pid": 101, "created_at": "2024-01-02T11:30:00Z"}
        for actual in (None, {"pid": 101}, {"pid": 101, "created_at": "2024-01-02T10:00:00Z"},
                       {"pid": 102, "created_at": expected["created_at"]}):
            with self.subTest(actual=actual):
                result = sample(instance_id=actual, expected_instance_id=expected)
                self.assertEqual(result["availability"], "unavailable")
                self.assertEqual(result["reason"], "instance_mismatch")
                self.assert_no_values(result)
        result = sample(instance_id=expected, expected_instance_id=expected)
        self.assertEqual(result["freshness"], "current")
        self.assertEqual(result["instance_id"], {"pid": 101, "created_at": "2024-01-02T11:30:00.000000Z"})

    def test_malformed_identity_cannot_match_through_boolean_coercion_or_emptiness(self):
        for actual, expected in ((1, True), (True, 1), ("", "")):
            with self.subTest(actual=actual, expected=expected):
                result = sample(instance_id=actual, expected_instance_id=expected)
                self.assertEqual(result["availability"], "unavailable")
                self.assertEqual(result["reason"], "instance_mismatch")
                self.assert_no_values(result)

    def test_process_identity_offsets_match_but_malformed_incarnations_do_not(self):
        expected = {"pid": 101, "created_at": "2024-01-02T11:00:00Z"}
        actual = {"pid": 101, "created_at": "2024-01-02T12:00:00+01:00"}
        result = sample(instance_id=actual, expected_instance_id=expected)
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["instance_id"], {"pid": 101, "created_at": "2024-01-02T11:00:00.000000Z"})
        invalid = [
            {"pid": True, "created_at": STAMP},
            {"pid": 101.0, "created_at": STAMP},
            {"pid": 0, "created_at": STAMP},
            {"pid": -1, "created_at": STAMP},
            {"pid": 0x100000000, "created_at": STAMP},
            {"pid": 101, "created_at": "2024-01-02T12:00:00"},
            {"pid": 101, "created_at": NOW},
            {"pid": 101, "created_at": "invalid"},
            {"pid": 101, "created_at": STAMP, "synthetic_private": "never echo"},
        ]
        for identity in invalid:
            with self.subTest(identity=repr(identity)):
                result = sample(instance_id=identity, expected_instance_id=identity)
                self.assertEqual(result["availability"], "unavailable")
                self.assertEqual(result["reason"], "instance_mismatch")
                self.assertIsNone(result["instance_id"])
                self.assert_no_values(result)
                self.assertNotIn("never echo", json.dumps(result))

    def test_output_identity_uses_validated_fields_when_mapping_mutates(self):
        class MutatingIdentity(dict):
            def __getitem__(self, key):
                value = super().__getitem__(key)
                if key == "pid":
                    self["unexpected_field"] = "synthetic_marker"
                return value

        identity = MutatingIdentity(pid=101, created_at=STAMP)
        result = sample(instance_id=identity)
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["instance_id"], {"pid": 101, "created_at": "2024-01-02T12:00:00.000000Z"})
        self.assertNotIn("synthetic_marker", json.dumps(result))

    def test_identity_tokens_are_bounded_and_invalid_ids_not_echoed(self):
        for token in ("synthetic-token", "x" * 256):
            result = sample(instance_id=token, expected_instance_id=token)
            self.assertEqual(result["availability"], "available")
            self.assertEqual(result["instance_id"], token)
        for identity in ("x" * 257, 101, True, [], {}):
            with self.subTest(identity=repr(identity)):
                result = sample(instance_id=identity)
                self.assertEqual(result["availability"], "unavailable")
                self.assertIsNone(result["instance_id"])
                self.assert_no_values(result)

    def test_minimized_is_not_invented_as_provider_unavailability_or_capability(self):
        result = sample()
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["capabilities"]["minimized_live_read"], "unverified")
        absent = d.tmog_snapshot(observed_at=NOW)
        self.assertEqual(absent["provider_id"], "tmog")
        self.assertEqual(absent["availability"], "unavailable")
        self.assertEqual(absent["reason"], "live_binding_unverified")
        self.assertEqual(absent["capabilities"]["minimized_live_read"], "unverified")
        self.assert_no_values(absent)


class VitalsRegressions(unittest.TestCase):
    def test_imported_os_fallback_keeps_zero_and_ignores_raw_gpu_and_cpu_seconds(self):
        result = d.from_vitals(vitals(), observed_at=NOW)
        self.assertEqual(result["provider_id"], "windows_vitals")
        self.assertEqual(result["provenance"], "imported")
        self.assertEqual(result["metrics"]["cpu_pct"]["value"], 0)
        self.assertEqual(result["metrics"]["ram_pct"]["value"], 60)
        self.assertEqual(result["metrics"]["editor_resident_bytes"]["value"], 0)
        self.assertIsNone(result["metrics"]["gpu_pct"]["value"])
        self.assertNotIn("cpu_s", json.dumps(result))
        self.assertNotIn("250", json.dumps(result["metrics"]))

    def test_recently_read_legacy_or_stale_export_is_never_current(self):
        for stamp, freshness in (("2024-01-02T12:00:00", "unknown"), (None, "unknown"),
                                 ("2024-01-02T11:59:00Z", "stale"), ("2024-01-02T12:00:01Z", "unknown")):
            with self.subTest(stamp=stamp):
                result = d.from_vitals(vitals(when=stamp), observed_at=NOW)
                self.assertEqual(result["freshness"], freshness)
                self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))

    def test_explicit_sample_time_can_establish_an_import_capture(self):
        result = d.from_vitals(vitals(when="naive legacy"), observed_at=NOW, sampled_at=NOW)
        self.assertEqual(result["freshness"], "current")
        self.assertEqual(result["provenance"], "imported")

    def test_failed_collector_partial_stdout_and_malformed_payload_are_unavailable(self):
        for payload, ok in ((vitals(), False), (vitals(), 1), (None, True), ([], True), ("{}", True), (5, True)):
            with self.subTest(payload=type(payload).__name__, ok=ok):
                result = d.from_vitals(payload, observed_at=NOW, collector_ok=ok)
                self.assertEqual(result["availability"], "failed")
                self.assertEqual(result["reason"], "collection_failed")
                self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))

    def test_invalid_memory_exports_do_not_emit_impossible_metrics(self):
        for changes in ({"total_mb": 0}, {"free_mb": 1100}, {"free_mb": -1}, {"total_mb": True},
                        {"total_mb": float("inf")}, {"free_mb": "0"}):
            with self.subTest(changes=changes):
                result = d.from_vitals(vitals(**changes), observed_at=NOW)
                for name in ("physical_total_bytes", "physical_available_bytes", "ram_pct"):
                    self.assertIsNone(result["metrics"][name]["value"])
                json.dumps(result, allow_nan=False)

    def test_missing_bad_or_ambiguous_process_rows_do_not_prove_editor_absence(self):
        for rows in (None, {}, [], [None], ["bad"], [{"ProcessName": "SyntheticOther", "mb": 0}],
                     [{"ProcessName": "UnrealEditor_Synthetic", "mb": 0}, {"ProcessName": "UnrealEditor_Second", "mb": 10}]):
            with self.subTest(rows=repr(rows)):
                result = d.from_vitals(vitals(top=rows), observed_at=NOW)
                self.assertIsNone(result["metrics"]["editor_resident_bytes"]["value"])
                self.assertEqual(result["metrics"]["editor_resident_bytes"]["status"], "missing")
                self.assertEqual(result["metrics"]["ram_pct"]["value"], 60)
                self.assertIsNone(result["instance_id"])


class OsFallbackRegressions(unittest.TestCase):
    def test_one_shot_windows_reader_preserves_os_provenance(self):
        with patch.object(d.os, "name", "nt"), patch.object(d, "_now", return_value=NOW), patch.object(d, "_windows_memory", return_value=SYSTEM_METRICS) as collector:
            result = d.collect_windows(observed_at=NOW)
        collector.assert_called_once_with()
        self.assertEqual(result["provider_id"], "windows_psapi")
        self.assertEqual(result["provenance"], "live")
        self.assertEqual(result["sampled_at"], result["observed_at"])
        self.assertEqual(result["capabilities"]["minimized_live_read"], "not_applicable")
        self.assertEqual(result["metrics"]["physical_available_bytes"]["value"], 0)
        self.assertEqual(result["metrics"]["committed_bytes"]["value"], 0)
        self.assertIsNone(result["metrics"]["cpu_pct"]["value"])

    def test_live_capture_time_is_not_replaced_by_observation_override(self):
        with patch.object(d.os, "name", "nt"), patch.object(d, "_now", return_value=NOW), patch.object(d, "_windows_memory", return_value=SYSTEM_METRICS):
            result = d.collect_windows(observed_at=NOW + timedelta(seconds=30))
        self.assertEqual(result["sampled_at"], "2024-01-02T12:00:00.000000Z")
        self.assertEqual(result["age_seconds"], 30)
        self.assertEqual(result["freshness"], "stale")
        self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))

    def test_nonwindows_or_failed_reader_never_fabricates_zero(self):
        with patch.object(d.os, "name", "posix"), patch.object(d, "_windows_memory") as collector:
            result = d.collect_windows(observed_at=NOW)
        collector.assert_not_called()
        self.assertEqual(result["availability"], "unsupported")
        self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))
        for error in (OSError("synthetic failure"), ValueError("synthetic malformed counter")):
            with self.subTest(error=type(error).__name__):
                with patch.object(d.os, "name", "nt"), patch.object(d, "_windows_memory", side_effect=error) as collector:
                    result = d.collect_windows(observed_at=NOW)
                collector.assert_called_once_with()
                self.assertEqual(result["availability"], "failed")
                self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))


class ArtifactRegressions(unittest.TestCase):
    def test_opaque_export_metadata_never_leaks_path_text_or_metrics(self):
        content = b'{"synthetic_secret":"never export me","cpu_pct":0}'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private_fixture.tmogtrace"
            path.write_bytes(content)
            result = d.artifact_snapshot(path, observed_at=NOW)
            exported = json.dumps(result, allow_nan=False)
            self.assertNotIn(str(path), exported)
            self.assertNotIn(path.name, exported)
        self.assertNotIn("never export me", exported)
        self.assertEqual(result["provider_id"], "tmog_artifact")
        self.assertEqual(result["provenance"], "imported")
        self.assertEqual(result["availability"], "unavailable")
        self.assertEqual(result["freshness"], "unavailable")
        self.assertIsNone(result["sampled_at"])
        self.assertEqual(result["artifact"]["availability"], "available")
        for key, value in {"kind": "opaque_trace", "size_bytes": len(content),
                           "sha256": hashlib.sha256(content).hexdigest(), "schema_verified": False}.items():
            self.assertEqual(result["artifact"][key], value)
        self.assertTrue(all(metric["value"] is None for metric in result["metrics"].values()))

    def test_exact_byte_budget_is_allowed_and_oversize_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.txt"
            path.write_bytes(b"12345678")
            exact = d.artifact_snapshot(path, observed_at=NOW, max_bytes=8)
            refused = d.artifact_snapshot(path, observed_at=NOW, max_bytes=7)
        self.assertEqual(exact["artifact"]["size_bytes"], 8)
        self.assertEqual(refused["reason"], "artifact_too_large")
        self.assertNotIn("artifact", refused)

    def test_missing_directory_and_links_are_not_usable_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = d.artifact_snapshot(root / "absent", observed_at=NOW)
            folder = d.artifact_snapshot(root, observed_at=NOW)
            path = root / "fixture.txt"
            path.write_bytes(b"data")
            with patch.object(Path, "is_symlink", return_value=True), patch.object(Path, "open", side_effect=AssertionError("must not open link")):
                linked = d.artifact_snapshot(path, observed_at=NOW)
        self.assertEqual(missing["reason"], "artifact_unreadable")
        self.assertEqual(folder["reason"], "not_regular_file")
        self.assertEqual(linked["reason"], "not_regular_file")
        self.assertTrue(all("artifact" not in result for result in (missing, folder, linked)))

    def test_changed_file_during_read_is_not_a_verified_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.txt"
            path.write_bytes(b"data")
            original = path.stat()
            final = SimpleNamespace(**{name: getattr(original, name) for name in (
                "st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")})
            final.st_size += 1
            with patch.object(d.os, "fstat", side_effect=[original, final]):
                result = d.artifact_snapshot(path, observed_at=NOW)
        self.assertEqual(result["reason"], "artifact_changed")
        self.assertNotIn("artifact", result)

    def test_replaced_opened_identity_is_refused_before_body_read(self):
        class UnselectedStream(io.BytesIO):
            def fileno(self):
                return 101

            def read(self, size=-1):
                raise AssertionError("must not read a replaced file")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.txt"
            path.write_bytes(b"data")
            original = path.stat()
            different = SimpleNamespace(**{name: getattr(original, name) for name in (
                "st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")})
            different.st_ino += 1
            with patch.object(Path, "open", return_value=UnselectedStream(b"not-selected")), patch.object(d.os, "fstat", return_value=different):
                result = d.artifact_snapshot(path, observed_at=NOW)
        self.assertEqual(result["reason"], "artifact_changed")
        self.assertNotIn("artifact", result)

    def test_growing_file_is_bounded_even_after_initial_size_check(self):
        class GrowingStream(io.BytesIO):
            def fileno(self):
                return 101

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.txt"
            path.write_bytes(b"data")
            original = path.stat()
            with patch.object(Path, "open", return_value=GrowingStream(b"123456789")), patch.object(d.os, "fstat", return_value=original):
                result = d.artifact_snapshot(path, observed_at=NOW, max_bytes=8)
        self.assertEqual(result["reason"], "artifact_too_large")
        self.assertNotIn("artifact", result)

    def test_bad_import_budgets_are_refused(self):
        for budget in (True, 0, -1, 1.5, d.MAX_ARTIFACT_BYTES + 1):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    d.artifact_snapshot("not-opened", observed_at=NOW, max_bytes=budget)


if __name__ == "__main__":
    unittest.main()
