# SPDX-License-Identifier: MIT
"""Real synthetic ZIP jobs and publication/refusal boundaries, without native I/O."""

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
from tools.world_package.job_cli import main
from tools.world_package import job_store
from tools.world_package.job_store import JobError, create_job, inspect_job
from tools.world_package.tests.fixtures import MANIFEST, package, receipt


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.source = package(self.sources / "fixture.zip")
        self.output = self.root / "job"

    def request(self, *paths, prior=()):
        return {"format": REQUEST_FORMAT, "version": 1,
                "packages": [{"key": "input-" + str(index), "package": str(path)}
                             for index, path in enumerate(paths or (self.source,))],
                "prior_receipts": list(prior)}

    def create(self, request=None, output=None):
        return create_job(request or self.request(), output or self.output, str(self.sources))

    def repin(self, job, name, data):
        (job / name).write_bytes(data)
        manifest = json.loads((job / "job.json").read_text())
        for pin in manifest["files"]:
            if pin["path"] == name:
                pin.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        encoded = encode_batch(manifest)
        (job / "job.json").write_bytes(encoded)
        (job / "job.pending.json").write_bytes(encoded)

    def test_relocated_job_survives_original_removal_and_never_reopens_sources(self):
        created = self.create()
        self.assertEqual(created, inspect_job(self.output))
        relocated = self.root / "relocated"
        shutil.move(str(self.output), relocated)
        shutil.rmtree(self.sources)
        original_open = Path.open

        def guarded(path, *args, **kwargs):
            if self.sources in path.parents:
                raise AssertionError("inspection reopened an original path")
            return original_open(path, *args, **kwargs)

        cwd = os.getcwd()
        with patch.object(Path, "open", guarded):
            self.assertEqual(created, inspect_job(relocated))
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, main(["inspect", str(relocated)]))
        self.assertEqual(cwd, os.getcwd())
        self.assertEqual(created["manifest"], json.loads(stdout.getvalue())["manifest"])
        self.assertEqual("packages/0000.zip", created["plan"]["items"][0]["package"])

    def test_exact_alias_receipt_and_deterministic_fresh_jobs_preserve_planner_contract(self):
        alias = self.sources / "alias.zip"
        alias.write_bytes(self.source.read_bytes())
        accepted = receipt(build_plan(self.source))
        request = self.request(self.source, alias, prior=[accepted])
        before = copy.deepcopy(request)
        result = self.create(request)
        self.assertEqual(result, self.create(request, self.root / "other-job"))
        self.assertEqual(before, request)
        self.assertEqual(1, result["plan"]["counts"]["no_op"])
        self.assertEqual(1, result["plan"]["counts"]["duplicate"])
        self.assertEqual(build_plan(self.source, accepted), result["plan"]["inventory"][0]["plan"])
        self.source.write_bytes(b"changed original after publication")
        self.assertEqual(result, inspect_job(self.output))

    def test_invalid_conflicting_and_existing_outputs_never_publish_or_overwrite(self):
        invalid = self.sources / "bad.zip"
        invalid.write_bytes(b"invalid zip")
        changed = package(self.sources / "conflict.zip", dict(MANIFEST, generator="different"))
        for index, request in enumerate((self.request(invalid), self.request(self.source, changed))):
            output = self.root / ("partial-" + str(index))
            with self.subTest(index=index), self.assertRaisesRegex(JobError, "frozen batch refused"):
                self.create(request, output)
            self.assertFalse((output / "job.json").exists())
            self.assertTrue((output / "provenance.json").exists())
            with self.assertRaises(JobError):
                inspect_job(output)
        result = self.create()
        original = (self.output / "job.json").read_bytes()
        with self.assertRaises(JobError):
            self.create()
        self.assertEqual(original, (self.output / "job.json").read_bytes())
        self.assertEqual(result, inspect_job(self.output))

    def test_tampering_extra_entries_and_repinned_receipt_mismatch_refuse(self):
        accepted = receipt(build_plan(self.source))
        self.create(self.request(prior=[accepted]))
        for name in ("packages/0000.zip", "request.json", "plan.json", "provenance.json"):
            target = self.root / ("tamper-" + name.replace("/", "-"))
            shutil.copytree(self.output, target)
            (target / name).write_bytes(b"tampered")
            with self.subTest(name=name), self.assertRaisesRegex(JobError, "size/hash mismatch"):
                inspect_job(target)
        target = self.root / "repinned"
        shutil.copytree(self.output, target)
        staged = json.loads((target / "request.json").read_text())
        staged["prior_receipts"] = []
        self.repin(target, "request.json", encode_batch(staged))
        with self.assertRaisesRegex(JobError, "keys/receipts differ"):
            inspect_job(target)
        (self.output / "extra.txt").write_text("unexpected")
        with self.assertRaisesRegex(JobError, "unexpected job entry"):
            inspect_job(self.output)

    def test_interrupted_or_unsupported_publication_preserves_unpublished_partial_files(self):
        with patch.object(job_store.os, "link", side_effect=OSError("injected link refusal")), \
                self.assertRaisesRegex(JobError, "unpublished"):
            self.create()
        self.assertTrue((self.output / "job.pending.json").exists())
        self.assertFalse((self.output / "job.json").exists())
        with self.assertRaises(JobError):
            inspect_job(self.output)
        with patch.object(job_store.os, "fsync", side_effect=OSError("injected flush refusal")), \
                self.assertRaises(JobError):
            self.create(output=self.root / "flush-partial")
        self.assertFalse((self.root / "flush-partial" / "job.json").exists())
        actual_link = os.link

        def committed_then_error(*args):
            actual_link(*args)
            raise OSError("injected error after publication")

        uncertain = self.root / "uncertain"
        with patch.object(job_store.os, "link", committed_then_error), \
                self.assertRaisesRegex(JobError, "publication uncertain"):
            self.create(output=uncertain)
        self.assertEqual("complete", inspect_job(uncertain)["manifest"]["state"])

    def test_copy_byte_caps_and_short_writes_stop_without_publication(self):
        size = self.source.stat().st_size
        with patch.object(job_store, "MAX_PACKAGE_BYTES", size - 1), self.assertRaisesRegex(JobError, "byte limit"):
            self.create()
        self.assertFalse((self.output / "job.json").exists())
        alias = self.sources / "alias.zip"
        alias.write_bytes(self.source.read_bytes())
        with patch.object(job_store, "MAX_PACKAGE_BYTES", 4096), \
                patch.object(job_store, "MAX_SOURCE_BYTES", 4097 + size - 1), \
                patch.object(job_store, "_copy", wraps=job_store._copy) as copied, \
                self.assertRaisesRegex(JobError, "before opening"):
            self.create(self.request(self.source, alias), self.root / "budget-partial")
        self.assertEqual(1, copied.call_count)
        original_open = Path.open

        @contextlib.contextmanager
        def short_open(path, *args, **kwargs):
            with original_open(path, *args, **kwargs) as stream:
                if args == ("xb",) and path.suffix == ".zip":
                    writer = type("ShortWriter", (), {"write": lambda _, data: stream.write(data[:-1])})()
                    yield writer
                else:
                    yield stream

        with patch.object(Path, "open", short_open), self.assertRaisesRegex(JobError, "short package copy"):
            self.create(output=self.root / "short-partial")
        self.assertFalse((self.root / "short-partial" / "job.json").exists())

    def test_cli_create_and_published_schema(self):
        request = self.root / "selection.json"
        request.write_bytes(encode_batch(self.request()))
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, main(["create", str(request), "--output", str(self.output)]))
        value = json.loads(stdout.getvalue())
        schema = json.loads((Path(job_store.__file__).parent / "job-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value["manifest"])
        value["manifest"]["native_acceptance"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(value["manifest"])


if __name__ == "__main__":
    unittest.main()
