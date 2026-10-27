# SPDX-License-Identifier: MIT

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

from tools.world_package import build_plan
from tools.world_package.batch_plan import REQUEST_FORMAT, encode_batch
from tools.world_package import job_compose
from tools.world_package.job_compose import CompositionError, compose_jobs, inspect_composite_job
from tools.world_package.job_compose_cli import main
from tools.world_package.job_store import create_job, inspect_job
from tools.world_package.tests.fixtures import MANIFEST, package, receipt


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.zip = package(self.sources / "one.zip")
        other = copy.deepcopy(MANIFEST)
        other["world"]["id"] = "world-other"
        self.other = package(self.sources / "two.zip", other)
        self.one = self.child("one", [self.zip])
        self.two = self.child("two", [self.other])
        self.output = self.root / "composite"

    def child(self, name, paths, prior=()):
        request = {"format": REQUEST_FORMAT, "version": 1, "prior_receipts": list(prior),
                   "packages": [{"key": "input-" + str(index), "package": str(path)} for index, path in enumerate(paths)]}
        output = self.sources / name
        create_job(request, output, str(self.sources))
        return output

    def selectors(self, one=None, two=None):
        return [{"key": "a/b", "job": str(one or self.one)}, {"key": "a_b", "job": str(two or self.two)}]

    def repin_outer(self, root, name, data):
        (root / name).write_bytes(data)
        marker = json.loads((root / "composite.json").read_text())
        for pin in marker["files"]:
            if pin["path"] == name:
                pin.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        encoded = encode_batch(marker)
        (root / "composite.json").write_bytes(encoded)
        (root / "composite.pending.json").write_bytes(encoded)

    def test_real_cli_composition_is_deterministic_relocatable_and_independent_of_sources(self):
        selected = self.selectors()
        result = compose_jobs(selected, self.output)
        self.assertEqual(result, compose_jobs(list(reversed(selected)), self.root / "same-selection"))
        keys = [item["key"] for item in result["aggregate"]["plan"]["items"]]
        self.assertEqual(2, len(set(keys)))
        self.assertEqual(["a/b", "a_b"], [item["key"] for item in result["lineage"]["children"]])
        cli_output = self.root / "cli-composite"
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, main(["create", "--child", "a/b", str(self.one), "--child", "a_b", str(self.two),
                                      "--output", str(cli_output)]))
        schema = json.loads((Path(job_compose.__file__).parent / "composite-job-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        value = json.loads(stdout.getvalue())
        Draft202012Validator(schema).validate(value["manifest"])
        value["manifest"]["native_acceptance"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(value["manifest"])
        relocated = self.root / "relocated"
        shutil.move(str(self.output), relocated)
        shutil.rmtree(self.sources)
        original_open = Path.open

        def guarded(path, *args, **kwargs):
            if self.sources in path.parents:
                raise AssertionError("reopened a child/original source")
            return original_open(path, *args, **kwargs)

        cwd = os.getcwd()
        with patch.object(Path, "open", guarded):
            self.assertEqual(result, inspect_composite_job(relocated))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(["inspect", str(relocated)]))
        self.assertEqual(cwd, os.getcwd())

    def test_aliases_and_full_receipt_union_preserve_individual_child_proposals(self):
        accepted = receipt(build_plan(self.zip))
        accepted_child = self.child("accepted", [self.zip], [accepted])
        result = compose_jobs(self.selectors(self.one, accepted_child), self.output)
        counts = result["aggregate"]["plan"]["counts"]
        self.assertEqual((1, 1), (counts["no_op"], counts["duplicate"]))
        copied_proposal = json.loads((self.output / "children/0000/plan.json").read_text())
        self.assertEqual(1, copied_proposal["counts"]["plan_new"])
        self.assertEqual(result, inspect_composite_job(self.output))
        another = self.child("also-accepted", [self.zip], [accepted])
        dedup = self.root / "dedup"
        compose_jobs(self.selectors(another, accepted_child), dedup)
        request = json.loads((dedup / "aggregate/request.json").read_text())
        self.assertEqual([accepted], request["prior_receipts"])

    def test_cross_job_zip_conflicts_and_receipt_witness_conflicts_refuse(self):
        changed = package(self.sources / "changed.zip", dict(MANIFEST, generator="different bytes"))
        conflicting = self.child("conflicting", [changed])
        with self.assertRaisesRegex(CompositionError, "conflicting package bytes"):
            compose_jobs(self.selectors(self.one, conflicting), self.output)
        self.assertFalse((self.output / "composite.json").exists())
        accepted = receipt(build_plan(self.zip))
        first = self.child("receipt-one", [self.zip], [accepted])
        second = self.child("receipt-two", [self.zip], [dict(accepted, acceptance_reference="different witness")])
        target = self.root / "receipt-conflict"
        with self.assertRaisesRegex(CompositionError, "conflicting accepted receipts"):
            compose_jobs(self.selectors(first, second), target)
        self.assertFalse((target / "aggregate").exists())
        self.assertFalse((target / "composite.json").exists())

    def test_pinned_tampering_and_repinned_lineage_mapping_refuse(self):
        compose_jobs(self.selectors(), self.output)
        for name in ("aggregate/packages/0000.zip", "children/0000/request.json"):
            target = self.root / ("tamper-" + name.replace("/", "-"))
            shutil.copytree(self.output, target)
            (target / name).write_bytes(b"tampered")
            with self.subTest(name=name), self.assertRaises(CompositionError):
                inspect_composite_job(target)
        lineage = json.loads((self.output / "lineage.json").read_text())
        lineage["children"][0]["items"][0]["aggregate_key"] = "forged-key"
        self.repin_outer(self.output, "lineage.json", encode_batch(lineage))
        with self.assertRaisesRegex(CompositionError, "manifest/key lineage mismatch"):
            inspect_composite_job(self.output)

    def test_changes_between_inspection_and_copy_never_publish_outer_completion(self):
        actual_create = job_compose.create_job
        original = (self.one / "packages/0000.zip").read_bytes()

        def changed_child(*args):
            (self.one / "packages/0000.zip").write_bytes(self.other.read_bytes())
            return actual_create(*args)

        with patch.object(job_compose, "create_job", changed_child), \
                self.assertRaisesRegex(CompositionError, "aggregate copy differs"):
            compose_jobs(self.selectors(), self.output)
        self.assertFalse((self.output / "composite.json").exists())
        self.assertTrue((self.output / "aggregate/job.json").exists())
        (self.one / "packages/0000.zip").write_bytes(original)

        def changed_copy(*args):
            result = actual_create(*args)
            (Path(args[1]) / "packages/0000.zip").write_bytes(b"corrupt copied bytes")
            return result

        target = self.root / "copy-tamper"
        with patch.object(job_compose, "create_job", changed_copy), self.assertRaises(CompositionError):
            compose_jobs(self.selectors(), target)
        self.assertFalse((target / "composite.json").exists())

    def test_outer_publication_failure_and_uncertainty_preserve_exact_stage(self):
        actual_link = os.link

        def denied_outer(source, target):
            if Path(target).name == "composite.json":
                raise OSError("injected outer publication failure")
            actual_link(source, target)

        with patch.object(job_compose.os, "link", denied_outer), \
                self.assertRaisesRegex(CompositionError, "nested aggregate marker exists"):
            compose_jobs(self.selectors(), self.output)
        self.assertTrue((self.output / "composite.pending.json").exists())
        self.assertFalse((self.output / "composite.json").exists())
        inspect_job(self.output / "aggregate")

        def uncertain(source, target):
            actual_link(source, target)
            if Path(target).name == "composite.json":
                raise OSError("injected error after outer publication")

        target = self.root / "uncertain"
        with patch.object(job_compose.os, "link", uncertain), self.assertRaisesRegex(CompositionError, "publication uncertain"):
            compose_jobs(self.selectors(), target)
        inspect_composite_job(target)
        before = (target / "composite.json").read_bytes()
        with self.assertRaises(CompositionError):
            compose_jobs(self.selectors(), target)
        self.assertEqual(before, (target / "composite.json").read_bytes())

    def test_global_limits_preflight_before_deep_child_inspection(self):
        nine = self.child("nine", [self.zip] * 9)
        eight = self.child("eight", [self.zip] * 8)
        with patch.object(job_compose, "inspect_job", side_effect=AssertionError("must refuse before deep inspect")), \
                self.assertRaisesRegex(CompositionError, "budgets"):
            compose_jobs(self.selectors(nine, eight), self.output)
        for field, limit in (("MAX_SOURCE_BYTES", 1), ("MAX_LINEAGE_BYTES", 1)):
            with patch.object(job_compose, field, limit), \
                    patch.object(job_compose, "inspect_job", side_effect=AssertionError("must refuse before deep inspect")), \
                    self.subTest(field=field), self.assertRaisesRegex(CompositionError, "budgets"):
                compose_jobs(self.selectors(), self.root / field)
        with self.assertRaisesRegex(CompositionError, "inside a selected child"):
            compose_jobs(self.selectors(), self.one / "forbidden")
        self.assertFalse((self.one / "forbidden").exists())


if __name__ == "__main__":
    unittest.main()
