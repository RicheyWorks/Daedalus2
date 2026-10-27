# SPDX-License-Identifier: MIT
"""Synthetic whole-archive integrity regressions; no native assets or imports."""

import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import zlib

from tools.world_package import PlanError, build_plan
from tools.world_package import reader_adapter
from tools.world_package.__main__ import main
from tools.world_package.archive_integrity import ArchiveIntegrityError, validate_archive_integrity
from tools.world_package.tests.fixtures import MANIFEST, glb, package, receipt


def corrupt_stored_member(path, name):
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(name)
    data = bytearray(path.read_bytes())
    n, e = struct.unpack_from("<HH", data, info.header_offset + 26)
    data[info.header_offset + 30 + n + e] ^= 1
    path.write_bytes(data)


def patch_member_field(path, name, local_offset, central_offset, value):
    """Change one known 32-bit field in both headers of a tiny synthetic ZIP."""
    with zipfile.ZipFile(path) as archive:
        entry = archive.getinfo(name)
    data = bytearray(path.read_bytes())
    struct.pack_into("<I", data, entry.header_offset + local_offset, value)
    end = data.rfind(b"PK\x05\x06")
    position = struct.unpack_from("<I", data, end + 16)[0]
    while data[position:position + 4] == b"PK\x01\x02":
        n, e, c = struct.unpack_from("<HHH", data, position + 28)
        if data[position + 46:position + 46 + n].decode() == name:
            struct.pack_into("<I", data, position + central_offset, value)
            path.write_bytes(data)
            return
        position += 46 + n + e + c
    raise AssertionError("synthetic member central header missing")


class ProbeStream(io.BytesIO):
    def __init__(self, data, *, read_error=None, close_error=None):
        super().__init__(data)
        self.requests = []
        self.actual_read = 0
        self.read_error = read_error
        self.close_error = close_error

    def read(self, size=-1):
        self.requests.append(size)
        if self.read_error is not None:
            raise self.read_error
        value = super().read(size)
        self.actual_read += len(value)
        return value

    def __exit__(self, *args):
        super().__exit__(*args)
        if self.close_error is not None:
            raise self.close_error


class ProbeArchive:
    def __init__(self, members, *, open_error=None):
        self.members = members
        self.open_error = open_error
        self.opened = []

    def infolist(self):
        return [item[0] for item in self.members]

    def open(self, entry, mode):
        self.opened.append(entry.filename)
        if self.open_error is not None:
            raise self.open_error
        return next(stream for info, stream in self.members if info is entry)


class ArchiveIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_unreferenced_bad_crc_refuses_before_plan(self):
        info = zipfile.ZipInfo("README.txt")
        info.compress_type = zipfile.ZIP_STORED
        source = package(self.root / "bad-extra.zip", extra=[(info, b"synthetic readme")])
        corrupt_stored_member(source, "README.txt")
        before = source.read_bytes()
        # This deliberately exercises ONLY the disposable stdlib consumer;
        # the implementation must not extract anything during preflight.
        with zipfile.ZipFile(source) as archive:
            with self.assertRaisesRegex(zipfile.BadZipFile, "README.txt"):
                archive.extractall(self.root / "disposable-extraction")
        self.assertEqual(before, source.read_bytes())
        with self.assertRaisesRegex(PlanError, "README.txt"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_valid_opaque_and_empty_extras_preserve_plan_replay_without_extraction(self):
        extras = [("README.txt", b""), ("opaque.bin", b"\xff\x00opaque\xfe"),
                  ("extras/not-a-model.glb", b"opaque data, not a declared GLB")]
        source = package(self.root / "opaque.zip", extra=extras)
        before = source.read_bytes()
        initial_names = sorted(path.name for path in self.root.iterdir())
        with patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("extraction attempted")), patch.object(zipfile.ZipFile, "extract", side_effect=AssertionError("extraction attempted")):
            plan = build_plan(source)
            prior = receipt(plan)
            prior_before = copy.deepcopy(prior)
            self.assertEqual(plan, build_plan(source))
            replay = build_plan(source, prior)
        self.assertEqual("no_op", replay["action"])
        self.assertEqual(plan["source"], replay["source"])
        self.assertEqual(plan["destination"], replay["destination"])
        self.assertEqual(prior_before, prior)
        self.assertEqual(hashlib.sha256(before).hexdigest(), plan["source"]["package_sha256"])
        self.assertEqual(before, source.read_bytes())
        self.assertEqual(initial_names, sorted(path.name for path in self.root.iterdir()))

    def test_refusal_preserves_prior_receipt_and_has_no_cli_plan_output(self):
        extra = zipfile.ZipInfo("README.txt")
        source = package(self.root / "prior.zip", extra=[(extra, b"synthetic readme")])
        prior = receipt(build_plan(source))
        prior_before = copy.deepcopy(prior)
        prior_path = self.root / "accepted.json"
        prior_path.write_text(json.dumps(prior), encoding="utf-8")
        prior_bytes = prior_path.read_bytes()
        corrupt_stored_member(source, extra.filename)
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, "README.txt.*CRC"):
            build_plan(source, prior)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(1, main([str(source), "--prior-receipt", str(prior_path)]))
        self.assertEqual("", stdout.getvalue())
        self.assertIn("README.txt", stderr.getvalue())
        self.assertEqual(prior_before, prior)
        self.assertEqual(prior_bytes, prior_path.read_bytes())
        self.assertEqual(before, source.read_bytes())

    def test_unreferenced_truncated_compressed_stream_refuses(self):
        extra = zipfile.ZipInfo("extras/compressed.bin")
        extra.compress_type = zipfile.ZIP_DEFLATED
        source = package(self.root / "truncated.zip", extra=[(extra, bytes(range(256)) * 8)])
        with zipfile.ZipFile(source) as archive:
            compressed = archive.getinfo(extra.filename).compress_size
        patch_member_field(source, extra.filename, 18, 20, compressed // 2)
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, "extras/compressed.bin"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_empty_member_bad_crc_refuses_even_at_exact_byte_budget(self):
        extra = zipfile.ZipInfo("empty.bin")
        source = package(self.root / "empty.zip", extra=[(extra, b"")])
        patch_member_field(source, extra.filename, 14, 16, 1)
        with zipfile.ZipFile(source) as archive:
            total = sum(entry.file_size for entry in archive.infolist())
        before = source.read_bytes()
        with patch.object(reader_adapter, "MAX_EXPANDED_BYTES", total), self.assertRaisesRegex(PlanError, "empty.bin.*CRC"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_actual_size_must_match_declared_size_even_when_backend_crc_passes(self):
        extra = zipfile.ZipInfo("README.txt")
        source = package(self.root / "size.zip", extra=[(extra, b"abcdef")])
        patch_member_field(source, extra.filename, 22, 24, 10)
        with zipfile.ZipFile(source) as archive:
            # The backend reaches EOF/valid CRC despite inconsistent size.
            self.assertEqual(b"abcdef", archive.read(extra.filename))
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, "README.txt.*streamed size"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_real_large_compressible_extra_uses_only_bounded_discarding_reads(self):
        source = package(self.root / "streamed.zip", extra=[("opaque.bin", b"x" * (3 * 65536 + 17))])
        before = source.read_bytes()
        original = zipfile.ZipExtFile.read
        requests = []
        def guarded(stream, size=-1):
            if stream.name == "opaque.bin":
                requests.append(size)
                self.assertGreater(size, 0)
                self.assertLessEqual(size, 65536)
            return original(stream, size)
        with patch.object(zipfile.ZipExtFile, "read", guarded):
            self.assertEqual("plan_new", build_plan(source)["action"])
        self.assertGreaterEqual(len(requests), 4)
        self.assertEqual(before, source.read_bytes())

    def test_existing_metadata_bound_precedes_all_member_opens(self):
        source = package(self.root / "over-limit.zip", extra=[("opaque.bin", b"x" * 50)])
        with patch.object(reader_adapter, "MAX_EXPANDED_BYTES", 1), patch.object(zipfile.ZipFile, "open", side_effect=AssertionError("opened before metadata guard")):
            with self.assertRaisesRegex(PlanError, "expanded-byte budget"):
                build_plan(source)

    def test_exact_unique_budget_is_not_double_charged_by_declared_payload_rereads(self):
        assets = [{"name": "ark", "file": "assets/ark.glb", "use": "mount"}]
        source = package(self.root / "exact.zip", dict(MANIFEST, assets=assets),
                         extra=[("assets/ark.glb", glb()), ("opaque.bin", b"\xff" * 31)])
        with zipfile.ZipFile(source) as archive:
            total = sum(entry.file_size for entry in archive.infolist())
        with patch.object(reader_adapter, "MAX_EXPANDED_BYTES", total):
            self.assertEqual("plan_new", build_plan(source)["action"])

    def test_actual_cumulative_overflow_reads_only_one_extra_byte_and_stops(self):
        first = ProbeStream(b"abcd")
        second = ProbeStream(b"efghij")
        archive = ProbeArchive([(SimpleNamespace(filename="one", file_size=4), first),
                                (SimpleNamespace(filename="two", file_size=2), second),
                                (SimpleNamespace(filename="later", file_size=0), ProbeStream(b""))])
        with self.assertRaisesRegex(ArchiveIntegrityError, "two.*cumulative"):
            validate_archive_integrity(archive, max_expanded_bytes=7)
        self.assertEqual(8, first.actual_read + second.actual_read)
        self.assertEqual(["one", "two"], archive.opened)
        self.assertEqual([4], second.requests)

    def test_actual_per_member_overflow_stops_one_byte_after_its_cap(self):
        stream = ProbeStream(b"abcdef")
        archive = ProbeArchive([(SimpleNamespace(filename="one", file_size=2), stream),
                                (SimpleNamespace(filename="later", file_size=0), ProbeStream(b""))])
        with self.assertRaisesRegex(ArchiveIntegrityError, "one.*per-member"):
            validate_archive_integrity(archive, max_expanded_bytes=100, max_member_bytes=3)
        self.assertEqual(4, stream.actual_read)
        self.assertEqual([4], stream.requests)
        self.assertEqual(["one"], archive.opened)

    def test_stream_open_read_and_close_errors_retain_member_name(self):
        for error in (EOFError("truncated stream"), zlib.error("corrupt compressed stream")):
            archive = ProbeArchive([(SimpleNamespace(filename="bad.bin", file_size=3), ProbeStream(b"abc", read_error=error))])
            with self.subTest(error=type(error).__name__), self.assertRaisesRegex(ArchiveIntegrityError, "bad.bin"):
                validate_archive_integrity(archive, max_expanded_bytes=10)
        for archive in (ProbeArchive([], open_error=OSError("not opened")),
                        ProbeArchive([(SimpleNamespace(filename="bad.bin", file_size=3), ProbeStream(b"abc", close_error=OSError("close failed")))])):
            if not archive.members:
                archive.members.append((SimpleNamespace(filename="bad.bin", file_size=3), ProbeStream(b"abc")))
            with self.assertRaisesRegex(ArchiveIntegrityError, "bad.bin"):
                validate_archive_integrity(archive, max_expanded_bytes=10)

    def test_early_eof_is_a_named_size_refusal(self):
        archive = ProbeArchive([(SimpleNamespace(filename="short.bin", file_size=7), ProbeStream(b"abc"))])
        with self.assertRaisesRegex(ArchiveIntegrityError, "short.bin.*streamed size"):
            validate_archive_integrity(archive, max_expanded_bytes=10)

    def test_exact_eof_zero_limits_and_invalid_configuration_boundaries(self):
        stream = ProbeStream(b"abc")
        archive = ProbeArchive([(SimpleNamespace(filename="exact.bin", file_size=3), stream)])
        self.assertEqual(3, validate_archive_integrity(archive, max_expanded_bytes=3))
        self.assertEqual([4, 1], stream.requests)
        empty = ProbeArchive([(SimpleNamespace(filename="empty.bin", file_size=0), ProbeStream(b""))])
        self.assertEqual(0, validate_archive_integrity(empty, max_expanded_bytes=0))
        for limit in (-1, True, 1.5):
            archive = ProbeArchive([])
            with self.subTest(limit=limit), self.assertRaises(ArchiveIntegrityError):
                validate_archive_integrity(archive, max_expanded_bytes=limit)
            self.assertEqual([], archive.opened)


if __name__ == "__main__":
    unittest.main()
