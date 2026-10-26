# SPDX-License-Identifier: MIT
"""Deterministic offline behavior and refusal tests; no geometry or native runtime."""

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from tools.world_census import census

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("fixtures")
DAY = "2026-10-26"


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.alpha = self.fixture("alpha.json")
        self.beta = self.fixture("beta.json")
        self.bindings = self.fixture("bindings.json")

    def fixture(self, name):
        path = self.root / name
        path.write_bytes((FIXTURES / name).read_bytes())
        return path

    def write(self, data, name="changed.json"):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def data(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def report(self, bindings=None):
        return census.build_census([self.alpha, self.beta], DAY, bindings)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "tools.world_census", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)

    def test_unassigned_counts_are_definitions_not_arks_or_file_names(self):
        report = self.report()
        self.assertEqual(report["totals"], {"worlds": 2, "realms": 0, "islands": 3, "asset_definitions": 3,
            "worlds_without_realm": 2, "assets_without_realm": 3, "assets_without_island": 3})
        self.assertEqual(report["realms"], [{"id": None, "worlds": 2, "islands": 3, "asset_definitions": 3}])
        self.assertEqual(report["worlds"][0]["islands"], [{"slot": 2, "asset_definitions": 0}, {"slot": 9, "asset_definitions": 0}])
        self.assertIsNone(report["worlds"][0]["assets"][0]["island_slot"])

    def test_explicit_bindings_and_independent_unknown_dimensions(self):
        report = self.report(self.bindings)
        self.assertEqual(report["totals"], {"worlds": 2, "realms": 1, "islands": 3, "asset_definitions": 3,
            "worlds_without_realm": 1, "assets_without_realm": 1, "assets_without_island": 2})
        alpha = report["worlds"][0]
        self.assertEqual(alpha["realm_id"], "synthetic-realm")
        self.assertEqual(alpha["islands"], [{"slot": 2, "asset_definitions": 1}, {"slot": 9, "asset_definitions": 0}])
        data = self.data(self.bindings)
        del data["worlds"][0]["realm_id"]
        placed_only = self.report(self.write(data))
        self.assertEqual(placed_only["totals"]["assets_without_realm"], 3)
        self.assertEqual(placed_only["totals"]["assets_without_island"], 2)
        data["worlds"][0]["realm_id"] = "realm"
        del data["worlds"][0]["assets"]
        self.assertEqual(self.report(self.write(data))["totals"]["assets_without_island"], 3)

    def test_determinism_and_duplicate_provenance(self):
        reformatted = self.write(self.data(self.alpha), "alpha-copy.json")
        first = census.build_census([self.alpha, self.beta, reformatted, self.alpha], DAY, self.bindings)
        second = census.build_census([reformatted, self.beta, self.alpha], DAY, self.bindings)
        self.assertEqual(census.render_json(first), census.render_json(second))
        self.assertEqual(census.render_csv(first), census.render_csv(second))
        self.assertEqual(first["totals"]["asset_definitions"], 3)
        self.assertEqual(len(first["sources"]), 3)
        self.assertEqual(len(first["worlds"][0]["source_sha256s"]), 2)
        self.assertEqual(first["bindings_sha256"], hashlib.sha256(self.bindings.read_bytes()).hexdigest())

    def test_shared_realm_aggregation_and_per_scope_provenance(self):
        bindings = self.data(self.bindings)
        bindings["worlds"].append({"world_id": "beta", "revision": 0, "realm_id": "synthetic-realm"})
        report = self.report(self.write(bindings))
        self.assertEqual(report["realms"], [{"id": "synthetic-realm", "worlds": 2, "islands": 3, "asset_definitions": 3}])
        report = self.report(self.bindings)
        rows = list(csv.DictReader(io.StringIO(census.render_csv(report))))
        known = next(r for r in rows if r["scope"] == "realm" and r["realm_id"] == "synthetic-realm")
        self.assertEqual(known["source_sha256s"], hashlib.sha256(self.alpha.read_bytes()).hexdigest())
        self.assertNotIn(hashlib.sha256(self.beta.read_bytes()).hexdigest(), known["source_sha256s"])

    def test_conflicting_payload_or_revision_refuses(self):
        for field, value in (("revision", 13), ("title", "changed")):
            with self.subTest(field=field):
                data = self.data(self.alpha)
                data["world"][field] = value
                with self.assertRaisesRegex(census.CensusError, "conflicting manifest or multiple revisions"):
                    census.build_census([self.alpha, self.write(data)], DAY)

    def test_bad_package_shapes_and_versions_refuse(self):
        mutations = [lambda d: d.update(format="other"), lambda d: d.update(version=2), lambda d: d.update(version=True),
            lambda d: d.update(world=[]), lambda d: d["world"].update(id=""), lambda d: d["world"].update(revision=True),
            lambda d: d["world"].update(revision=-1), lambda d: d.update(assets=None), lambda d: d.update(islands={}),
            lambda d: d["islands"][0].update(slot=True), lambda d: d["islands"].append(d["islands"][0]),
            lambda d: d["assets"].append(d["assets"][0]), lambda d: d["assets"][0].update(use=3)]
        for mutation in mutations:
            data = self.data(self.alpha)
            mutation(data)
            with self.subTest(data=data), self.assertRaises(census.CensusError):
                census.build_census([self.write(data)], DAY)

    def test_package_asset_paths_are_relative_but_never_opened(self):
        for file in ("../secret.glb", "/absolute.glb", "https://example.org/a", "C:\\a.glb", "a//b", "a/./b"):
            data = self.data(self.alpha)
            data["assets"][0]["file"] = file
            with self.subTest(file=file), self.assertRaisesRegex(census.CensusError, "relative package path"):
                census.build_census([self.write(data)], DAY)
        self.assertEqual(self.report()["totals"]["asset_definitions"], 3)  # No .glb files exist.

    def test_binding_refusals(self):
        changes = [lambda d: d.update(version=2), lambda d: d.update(version=True), lambda d: d.update(extra="typo"),
            lambda d: d["worlds"][0].update(world_id="missing"), lambda d: d["worlds"][0].update(revision=11),
            lambda d: d["worlds"][0].update(realm_id=None), lambda d: d["worlds"][0].update(unknown=0),
            lambda d: d["worlds"].append(copy.deepcopy(d["worlds"][0])),
            lambda d: d["worlds"][0]["assets"][0].update(name="missing"),
            lambda d: d["worlds"][0]["assets"][0].update(island_slot=4),  # Exists only in beta.
            lambda d: d["worlds"][0]["assets"][0].update(island_slot=True),
            lambda d: d["worlds"][0]["assets"].append(copy.deepcopy(d["worlds"][0]["assets"][0]))]
        for change in changes:
            data = self.data(self.bindings)
            change(data)
            with self.subTest(data=data), self.assertRaises(census.CensusError):
                self.report(self.write(data))

    def test_asset_identity_includes_name_and_file(self):
        data = self.data(self.alpha)
        data["assets"].append({"name": "ark", "file": "assets/other.glb", "use": "a second definition"})
        path = self.write(data)
        report = census.build_census([path], DAY, self.bindings)
        self.assertEqual(report["totals"]["asset_definitions"], 3)
        self.assertEqual([a["island_slot"] for a in report["worlds"][0]["assets"]], [2, None, None])

    def test_empty_world_arrays_are_valid(self):
        data = self.data(self.alpha)
        del data["assets"]
        del data["islands"]
        report = census.build_census([self.write(data)], DAY)
        self.assertEqual(report["totals"]["asset_definitions"], 0)
        self.assertEqual(report["totals"]["islands"], 0)

    def test_invalid_json_is_precise_and_does_not_write(self):
        for raw, message in ((b'{"format":1,"format":2}', "duplicate JSON key"),
                             (b'{"x":NaN}', "nonfinite JSON"), (b'{"x":Infinity}', "nonfinite JSON"),
                             (b'{"x":1e999}', "Out of range float"), (b'[]', "expected an object"),
                             (b'\xff', "utf-8"), (b'{', "Expecting")):
            path = self.root / "bad.json"
            path.write_bytes(raw)
            out = self.root / "refused"
            result = self.cli(self.alpha, path, "--snapshot-date", DAY, "--output-dir", out)
            with self.subTest(raw=raw):
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(out.exists())
                self.assertEqual(path.read_bytes(), raw)

    def test_date_and_input_limits(self):
        for day in ("2026-02-29", "2026-1-02", "20261026", "2026-10-26T00:00:00"):
            with self.subTest(day=day), self.assertRaisesRegex(census.CensusError, "snapshot date"):
                census.build_census([self.alpha], day)
        for manifests in ([], [self.alpha] * (census.MAX_MANIFESTS + 1)):
            with self.assertRaisesRegex(census.CensusError, "supply between"):
                census.build_census(manifests, DAY)
        with patch.object(census, "MAX_INPUT_BYTES", 8), self.assertRaisesRegex(census.CensusError, "byte input limit"):
            self.report()
        with self.assertRaisesRegex(census.CensusError, "regular JSON file"):
            census.build_census([self.root], DAY)

    def test_cli_success_and_input_preservation(self):
        originals = {p: p.read_bytes() for p in (self.alpha, self.beta, self.bindings)}
        out = self.root / "snapshot"
        result = self.cli(self.beta, self.alpha, "--bindings", self.bindings, "--snapshot-date", DAY, "--output-dir", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((out / "census.json").read_text(encoding="utf-8"), census.render_json(self.report(self.bindings)))
        rows = list(csv.DictReader(io.StringIO((out / "daily.csv").read_text(encoding="utf-8"))))
        self.assertEqual([r["scope"] for r in rows], ["total", "realm", "realm", "world", "island", "island", "unassigned_island", "world", "island", "unassigned_island"])
        self.assertEqual(rows[0]["asset_definitions"], "3")
        self.assertEqual(rows[0]["assets_without_island"], "2")
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)

    def test_existing_outputs_input_alias_and_missing_parent_refuse(self):
        report = self.report()
        for target in (self.root, self.alpha, self.root / "missing-parent" / "snapshot"):
            with self.subTest(target=target), self.assertRaisesRegex(census.CensusError, "fresh output directory"):
                census.write_reports(report, target)
        out = self.root / "existing"
        out.mkdir()
        sentinel = out / "daily.csv"
        sentinel.write_bytes(b"preserve this report")
        with self.assertRaises(census.CensusError):
            census.write_reports(report, out)
        self.assertEqual(sentinel.read_bytes(), b"preserve this report")
        self.assertFalse((out / "census.json").exists())

    def test_invalid_binding_cli_creates_no_bundle(self):
        bad = self.data(self.bindings)
        bad["worlds"][0]["revision"] = 99
        out = self.root / "refused"
        result = self.cli(self.alpha, "--bindings", self.write(bad), "--snapshot-date", DAY, "--output-dir", out)
        self.assertEqual(result.returncode, 2)
        self.assertIn("binding revision", result.stderr)
        self.assertFalse(out.exists())

    def test_partial_write_error_is_reported_without_overwrite_or_cleanup(self):
        out = self.root / "partial"
        original_open = Path.open

        def fail_second(path, *args, **kwargs):
            if path.name == "daily.csv":
                raise OSError("simulated full disk")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", fail_second), self.assertRaisesRegex(census.CensusError, "partial new bundle preserved"):
            census.write_reports(self.report(), out)
        self.assertTrue((out / "census.json").exists())
        self.assertFalse((out / "daily.csv").exists())

    def test_output_reservation_and_file_creation_races_preserve_other_bytes(self):
        report = self.report()
        out = self.root / "directory-race"
        original_mkdir = Path.mkdir

        def reserve_first(path, *args, **kwargs):
            original_mkdir(path, *args, **kwargs)
            (path / "sentinel").write_bytes(b"other writer")
            return original_mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", reserve_first), self.assertRaisesRegex(census.CensusError, "fresh output directory"):
            census.write_reports(report, out)
        self.assertEqual((out / "sentinel").read_bytes(), b"other writer")
        self.assertFalse((out / "census.json").exists())
        original_open = Path.open
        raced = self.root / "file-race"

        def create_first(path, *args, **kwargs):
            if path.name == "census.json":
                with original_open(path, "wb") as stream:
                    stream.write(b"other file writer")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", create_first), self.assertRaisesRegex(census.CensusError, "partial new bundle preserved"):
            census.write_reports(report, raced)
        self.assertEqual((raced / "census.json").read_bytes(), b"other file writer")
        self.assertFalse((raced / "daily.csv").exists())

    def test_spreadsheet_formula_prefixes_are_neutralized(self):
        for identity in ("=1+1", "+SUM(A1)", "-1+2", "@formula", " \t=1+1", "\r\n@formula", "\x01=1+1", "\ufeff+1"):
            data = self.data(self.alpha)
            data["world"]["id"] = identity
            report = census.build_census([self.write(data)], DAY)
            csv_rows = list(csv.DictReader(io.StringIO(census.render_csv(report))))
            self.assertEqual(next(r for r in csv_rows if r["scope"] == "world")["world_id"], "'" + identity)
            self.assertEqual(json.loads(census.render_json(report))["worlds"][0]["id"], identity)

    def test_published_schemas_validate_and_reject_bad_contracts(self):
        report_schema = json.loads((ROOT / "schemas/world-census-v1.schema.json").read_text(encoding="utf-8"))
        bindings_schema = json.loads((ROOT / "schemas/world-census-bindings-v1.schema.json").read_text(encoding="utf-8"))
        for schema in (report_schema, bindings_schema):
            Draft202012Validator.check_schema(schema)
        report_validator = Draft202012Validator(report_schema, format_checker=FormatChecker())
        binding_validator = Draft202012Validator(bindings_schema)
        for report in (self.report(), self.report(self.bindings)):
            report_validator.validate(report)
        binding_validator.validate(self.data(self.bindings))
        bad = self.report()
        bad["totals"]["worlds"] = True
        self.assertFalse(report_validator.is_valid(bad))
        bad = self.report()
        bad["snapshot_date"] = "2026-02-29"
        self.assertFalse(report_validator.is_valid(bad))
        bad = self.data(self.bindings)
        bad["worlds"][0]["extra"] = 0
        self.assertFalse(binding_validator.is_valid(bad))


if __name__ == "__main__":
    unittest.main()
