# SPDX-License-Identifier: MIT
"""Secondary payload regressions use synthetic packages, never native content."""

import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from tools.world_package import PlanError, build_plan
from tools.world_package.__main__ import main
from tools.world_package import reader_adapter
from tools.world_package.tests.fixtures import MANIFEST, glb, package, receipt


def container(raw_json, chunks=()):
    """Build a synthetic container, retaining explicit chunk bytes for bad cases."""
    payload = raw_json + b" " * (-len(raw_json) % 4)
    body = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    for kind, data in chunks:
        body += struct.pack("<II", len(data), kind) + data
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def asset_package(self, payload, compression=zipfile.ZIP_STORED, world=None):
        manifest = copy.deepcopy(MANIFEST)
        manifest["assets"] = [{"name": "ark", "file": "assets/ark.glb", "use": "mount"}]
        stored = zipfile.ZipInfo("assets/ark.glb")
        stored.compress_type = compression
        return package(self.root / "asset.zip", manifest, glb_data=world, extra=[(stored, payload)])

    def assert_refused(self, payload, primary=False):
        source = self.asset_package(glb() if primary else payload, world=payload if primary else None)
        before = source.read_bytes()
        member = "world.glb" if primary else "assets/ark.glb"
        with self.assertRaises(PlanError) as error:
            build_plan(source)
        self.assertIn(member, str(error.exception))
        self.assertEqual(before, source.read_bytes())

    def test_malformed_secondary_bytes_refuse_with_member_name(self):
        source = self.asset_package(b"not-a-GLB")
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, r"assets/ark\.glb.*too short"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_valid_secondary_materials_transforms_bin_and_extension_preserved(self):
        rich = {"asset": {"version": "2.0"},
                "nodes": [{"translation": [1.5, -2, 0], "rotation": [0, 0, 0, 1], "scale": [2, 1, 3]}],
                "materials": [{"name": "SyntheticCopper", "pbrMetallicRoughness": {
                    "baseColorFactor": [0.8, 0.5, 0.2, 1], "metallicFactor": 0.9, "roughnessFactor": 0.3}}],
                "buffers": [{"byteLength": 4}]}
        payload = container(json.dumps(rich).encode(), [(0x004E4942, b"\x01\x02\x03\x04"), (0x12345678, b"abcd")])
        source = self.asset_package(payload)
        before = source.read_bytes()
        new = build_plan(source)
        accepted = receipt(new)
        saved_receipt = copy.deepcopy(accepted)
        again = build_plan(source)
        replay = build_plan(source, accepted)
        self.assertEqual(new, again)
        self.assertEqual("no_op", replay["action"])
        self.assertEqual(new["source"], replay["source"])
        self.assertEqual(new["destination"], replay["destination"])
        self.assertEqual(hashlib.sha256(before).hexdigest(), new["source"]["package_sha256"])
        self.assertEqual(saved_receipt, accepted)
        self.assertEqual(before, source.read_bytes())
        with zipfile.ZipFile(source) as archive:
            self.assertEqual(payload, archive.read("assets/ark.glb"))

    def test_primary_secondary_container_refusal_parity(self):
        valid = glb()
        bad_magic = bytearray(valid)
        struct.pack_into("<I", bad_magic, 0, 0)
        bad_version = bytearray(valid)
        struct.pack_into("<I", bad_version, 4, 1)
        wrong_length = bytearray(valid)
        struct.pack_into("<I", wrong_length, 8, len(valid) + 4)
        json_overflow = bytearray(valid)
        struct.pack_into("<I", json_overflow, 12, len(valid))
        wrong_first = bytearray(valid)
        struct.pack_into("<I", wrong_first, 16, 0x004E4942)
        raw = b'{"asset":{"version":"2.0"},"nodes":[]}'
        short_header = bytearray(container(raw) + b"tail")
        struct.pack_into("<I", short_header, 8, len(short_header))
        variants = [bytes(bad_magic), bytes(bad_version), bytes(wrong_length), valid[:-1],
                    bytes(json_overflow), bytes(wrong_first), bytes(short_header),
                    container(raw, [(0x004E4942, b"abc")]),
                    container(raw, [(0x4E4F534A, b"{}  ")]),
                    container(raw, [(0x004E4942, b"1234"), (0x004E4942, b"5678")]),
                    container(raw, [(0x12345678, b"abcd"), (0x004E4942, b"1234")])]
        for index, payload in enumerate(variants):
            for primary in (False, True):
                with self.subTest(variant=index, primary=primary):
                    self.assert_refused(payload, primary)

    def test_malformed_secondary_strict_json_refuses(self):
        variants = [b'{"asset":{"version":"1.0"}}', b'{"asset":{"version":"2.0"},"asset":{}}',
                    b'{"asset":{"version":"2.0"},"x":NaN}',
                    b'{"asset":{"version":"2.0"},"x":Infinity}',
                    b'{"asset":{"version":"2.0"},"x":1e999}',
                    b'{"asset":{"version":"2.0"},"x":' + b"9" * 1000 + b"}",
                    b'{"asset":{"version":"2.0"},"nodes":{}}', b"[]", b"{bad", b"\xff"]
        for value in variants:
            with self.subTest(value=value[:60]):
                self.assert_refused(container(value))

    def test_zero_length_bin_and_opaque_extension_boundaries_accepted(self):
        raw = b'{"asset":{"version":"2.0"}}'
        for chunks in ([], [(0x004E4942, b"")], [(0x12345678, b"abcd")],
                       [(0x004E4942, b"1234"), (0x12345678, b"")]):
            with self.subTest(chunks=chunks):
                self.assertEqual("plan_new", build_plan(self.asset_package(container(raw, chunks)))["action"])

    def test_expansion_bound_refuses_before_any_payload_read(self):
        source = self.asset_package(glb())
        before = source.read_bytes()
        with patch.object(reader_adapter, "MAX_EXPANDED_BYTES", 1), patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("payload read before bound")):
            with self.assertRaisesRegex(PlanError, "expanded-byte budget"):
                build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_secondary_decompressor_error_is_named_plan_error(self):
        source = self.asset_package(glb(), compression=zipfile.ZIP_DEFLATED)
        before = source.read_bytes()
        original = zipfile.ZipFile.read
        def broken(archive, name, *args, **kwargs):
            if name == "assets/ark.glb":
                raise zlib.error("synthetic corrupt compressed stream")
            return original(archive, name, *args, **kwargs)
        with patch.object(zipfile.ZipFile, "read", broken), self.assertRaisesRegex(PlanError, r"assets/ark\.glb.*compressed stream"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_actual_compressed_secondary_corruption_refuses(self):
        source = self.asset_package(glb(), compression=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(source) as archive:
            entry = archive.getinfo("assets/ark.glb")
        data = bytearray(source.read_bytes())
        n, e = struct.unpack_from("<HH", data, entry.header_offset + 26)
        data[entry.header_offset + 30 + n + e] = 0xff
        source.write_bytes(data)
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, r"assets/ark\.glb"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())

    def test_cli_refusal_has_no_plan_output_or_source_mutation(self):
        source = self.asset_package(b"not-a-GLB")
        before = source.read_bytes()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(1, main([str(source)]))
        self.assertEqual("", stdout.getvalue())
        self.assertIn("assets/ark.glb", stderr.getvalue())
        self.assertEqual(before, source.read_bytes())

    def test_damaged_declared_secondary_crc_refuses_with_member_name(self):
        source = self.asset_package(glb())
        with zipfile.ZipFile(source) as archive:
            entry = archive.getinfo("assets/ark.glb")
        data = bytearray(source.read_bytes())
        name_length, extra_length = struct.unpack_from("<HH", data, entry.header_offset + 26)
        start = entry.header_offset + 30 + name_length + extra_length
        data[start + entry.file_size - 1] ^= 1
        source.write_bytes(data)
        before = source.read_bytes()
        with self.assertRaisesRegex(PlanError, r"assets/ark\.glb.*CRC"):
            build_plan(source)
        self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
