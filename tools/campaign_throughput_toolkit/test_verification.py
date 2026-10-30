"""Synthetic correctness checks; no campaign or native files are opened."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from tools.campaign_throughput_toolkit.verification import VerificationError, verify


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.old = self.root / "old.source"
        self.previous = self.root / "previous.fbx"
        self.receipt = self.root / "previous.json"
        self.old.write_bytes(b"old retained source")
        self.previous.write_bytes(b"previous source bytes")
        self.receipt.write_bytes(b'{"synthetic":true}')
        self.pins = [self.pin(path) for path in (self.old, self.previous, self.receipt)]
        self.previous_pin = dict(self.pins[1])
        self.receipt_pin = dict(self.pins[2])

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def run_check(self, *, chunk=1, state=None, **kwargs):
        options = {"roots": [self.root], "chunk": chunk, "state": state}
        if chunk > 1:
            options.update(
                previous_chunk=chunk - 1,
                previous_receipt=self.receipt_pin,
                previous_files=[self.previous_pin],
            )
        options.update(kwargs)
        return verify(self.pins, **options)

    def test_initial_full_then_metadata_reuse_and_no_input_mutation(self):
        before_pins = copy.deepcopy(self.pins)
        first, cache = self.run_check()
        before_cache = copy.deepcopy(cache)
        second, next_cache = self.run_check(chunk=2, state=cache)
        self.assertEqual(first["mode"], "full")
        self.assertEqual(first["hashed_files"], 3)
        self.assertEqual(second["mode"], "incremental_metadata_reuse")
        self.assertEqual(second["hashed_files"], 2)
        self.assertEqual(second["previous_files_hashed"], 1)
        self.assertEqual(second["metadata_reused_files"], 1)
        self.assertFalse(second["continuous_content_verification"])
        self.assertEqual(self.pins, before_pins)
        self.assertEqual(cache, before_cache)
        self.assertEqual(next_cache["last_full_chunk"], 1)

    def test_flipped_previous_bytes_fail_even_with_preserved_mtime(self):
        _, cache = self.run_check()
        original = self.previous.stat()
        raw = self.previous.read_bytes()
        self.previous.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        os.utime(self.previous, ns=(original.st_atime_ns, original.st_mtime_ns))
        with self.assertRaisesRegex(VerificationError, "hash mismatch"):
            self.run_check(chunk=2, state=cache)

    def test_flipped_previous_receipt_fails(self):
        _, cache = self.run_check()
        self.receipt.write_bytes(b'{"synthetic":fals}')
        with self.assertRaisesRegex(VerificationError, "hash mismatch"):
            self.run_check(chunk=2, state=cache)

    def test_full_checkpoint_detects_older_same_size_byte_flip(self):
        _, cache = self.run_check(chunk=24, phase="start")
        original = self.old.stat()
        raw = self.old.read_bytes()
        self.old.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        os.utime(self.old, ns=(original.st_atime_ns, original.st_mtime_ns))
        with self.assertRaisesRegex(VerificationError, "hash mismatch"):
            self.run_check(chunk=25, state=cache)

    def test_checkpoint_and_start_stop_explicit_full(self):
        _, cache = self.run_check(chunk=24, phase="start")
        checkpoint, cache = self.run_check(chunk=25, state=cache)
        self.assertIn("scheduled_checkpoint", checkpoint["full_reasons"])
        self.assertEqual(checkpoint["hashed_files"], 3)
        stop, cache = self.run_check(chunk=25, state=cache, phase="stop")
        self.assertIn("stop", stop["full_reasons"])
        explicit, _ = self.run_check(chunk=26, state=cache, full=True)
        self.assertIn("explicit_full", explicit["full_reasons"])

    def test_metadata_only_change_hashes_known_file(self):
        _, cache = self.run_check()
        info = self.old.stat()
        os.utime(self.old, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
        report, _ = self.run_check(chunk=2, state=cache)
        self.assertEqual(report["hashed_files"], 3)
        self.assertEqual(len(report["changed_metadata_files_hashed"]), 1)

    def test_unknown_file_is_not_automatically_pinned(self):
        _, cache = self.run_check()
        (self.root / "unexpected.bin").write_bytes(b"unknown")
        with self.assertRaisesRegex(VerificationError, "unknown="):
            self.run_check(chunk=2, state=cache)

    def test_explicit_new_pin_is_fully_hashed(self):
        _, cache = self.run_check()
        new = self.root / "explicit.fbx"
        new.write_bytes(b"new source")
        self.pins.append(self.pin(new))
        report, _ = self.run_check(chunk=2, state=cache)
        self.assertEqual(len(report["new_files_hashed"]), 1)
        self.assertEqual(report["hashed_files"], 3)
        self.pins[-1]["sha256"] = "0" * 64
        with self.assertRaisesRegex(VerificationError, "hash mismatch"):
            self.run_check(chunk=2, state=cache)

    def test_removed_or_changed_old_pin_refused(self):
        _, cache = self.run_check()
        kept = self.pins.pop(0)
        with self.assertRaisesRegex(VerificationError, "pin removed"):
            self.run_check(chunk=2, state=cache)
        self.pins.insert(0, kept)
        self.pins[0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(VerificationError, "pin changed"):
            self.run_check(chunk=2, state=cache)

    def test_malformed_cache_and_changed_policy_fail_closed(self):
        _, cache = self.run_check()
        malformed = copy.deepcopy(cache)
        malformed["records"].pop(next(iter(malformed["records"])))
        with self.assertRaisesRegex(VerificationError, "coverage differs"):
            self.run_check(chunk=2, state=malformed)
        with self.assertRaisesRegex(VerificationError, "cadence differs"):
            self.run_check(chunk=2, state=cache, full_every=30)
        with self.assertRaisesRegex(VerificationError, "Unsupported or malformed"):
            self.run_check(chunk=2, state={})

    def test_previous_identity_and_pin_mismatch_refused(self):
        _, cache = self.run_check()
        for options in (
            {"previous_chunk": 99},
            {"previous_receipt": None},
            {"previous_files": []},
            {"previous_files": [{**self.pins[1], "sha256": "0" * 64}]},
        ):
            with self.subTest(options=options), self.assertRaises(VerificationError):
                self.run_check(chunk=2, state=cache, **options)

    def test_skipped_checkpoint_forces_full_regression_refused(self):
        _, cache = self.run_check()
        report, later = self.run_check(chunk=27, state=cache)
        self.assertEqual(report["mode"], "full")
        self.assertIn("checkpoint_gap", report["full_reasons"])
        with self.assertRaisesRegex(VerificationError, "regressing"):
            self.run_check(chunk=26, state=later)

    def test_missing_file_and_duplicate_pins_refused(self):
        self.pins.append(dict(self.pins[0]))
        with self.assertRaisesRegex(VerificationError, "Duplicate pin"):
            self.run_check()
        self.pins.pop()
        self.old.unlink()
        with self.assertRaisesRegex(VerificationError, "Cannot inspect"):
            self.run_check()

    def test_root_escape_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "external"
            external.write_bytes(b"outside")
            with self.assertRaisesRegex(VerificationError, "outside supplied"):
                verify([self.pin(external)], roots=[self.root], chunk=1)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "external"
            external.write_bytes(b"outside")
            link = self.root / "link"
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest("Symlink creation unavailable for current account")
            with self.assertRaisesRegex(VerificationError, "Symlink or reparse"):
                self.run_check()


if __name__ == "__main__":
    unittest.main()
