# SPDX-License-Identifier: MIT
"""Legacy wrapper and wire parity for the shared portable-path decision.

Expected diagnostics and digests were captured from the original callers on
main cbdc9d862caeb8b3a7bc43a2c60c891b4e157649 before extraction. These tests
exercise those callers, not a copy of the extracted policy implementation.
"""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from . import contracts, packet
from .test_takeover import fixture


FIELD_MESSAGE = " must be a nonempty string without control characters (max 4096)"
PORTABLE_MESSAGE = " must be a portable relative evidence path (max 220 ASCII characters)"
NORMALIZED_MESSAGE = " must be a normalized relative POSIX path"
FILESYSTEM_MESSAGE = " is not portable between supported filesystems"
DEVICE_MESSAGE = " uses a reserved device name"

FIXTURE_CHECKPOINT_SHA256 = "1c7defa756b1043bdd7baf59fef1e59c9decadf1db978fdf31a309a8ffe99b70"
FIXTURE_PACKET_SHA256 = "cd86f424410c8da7f0d2f2165128b2d616ccc1e671044195d46fee36cc9c3b7a"
FIXTURE_POINTER_SHA256 = "0f0efcaebe9e857a111c72814bcceb00fe54a22db2b08646c356962ab1c65830"
EXAMPLE_CHECKPOINT_SHA256 = "3e7a4a166835b81145de157882ac20767ea84e8e6ad9bedcb5a314665c4d910b"
EXAMPLE_PACKET_SHA256 = "d27ea9a460e5788e17f1e5eae481ffa7a3397d4f459dc5ecce845cd0bda55730"
EXAMPLE_POINTER_SHA256 = "eba0c26152fd2c56eb11a8bee70003bfe6bc54e2ba9bcc66b04a48799d7b03df"


class PathText(str):
    """Make packet.relative's original-object return contract observable."""


class EvidencePathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="handoff-evidence-paths-",
                                                 dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def rejected(self, value, contract_message, *, packet_format=False, at="evidence"):
        code = "INVALID_FIELD" if contract_message == FIELD_MESSAGE else "INVALID_PATH"
        with self.assertRaises(contracts.ContractError) as caught:
            contracts._path(value, at)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), at + contract_message)
        with self.assertRaises(contracts.ContractError) as caught:
            packet.relative(value)
        self.assertEqual(caught.exception.code, "unsafe_path")
        expected = ("Expected a portable relative evidence path: " + repr(value)
                    if packet_format else "Unsafe evidence path: " + value)
        self.assertEqual(str(caught.exception), expected)

    def test_accepted_paths_keep_both_return_contracts_and_object_identity(self):
        cases = ("A", "a/b", "a-b.c_d/0..9/file.JSON", "a...b", "a" * 220,
                 "COM0", "COM10", "COM01", "LPT0", "LPT10", "CONSOLE", "AUXiliary",
                 "COM1a", "x.CON", "a/com-1.json", "a/NUL_backup.txt", PathText("nested/Owner.json"))
        for value in cases:
            with self.subTest(value=value):
                self.assertIsNone(contracts._path(value, "evidence"))
                self.assertIs(packet.relative(value), value)

    def test_string_type_budget_control_and_ascii_precheck_priority_is_unchanged(self):
        field_cases = (None, True, False, 17, b"a", ["a"], {}, "", " ", "\u2003", "\u00a0",
                       "a" * 4097, "a" * 221 + "\x00")
        for value in field_cases:
            with self.subTest(value=repr(value)[:80]):
                self.rejected(value, FIELD_MESSAGE, packet_format=True)
        for ordinal in range(32):
            with self.subTest(control=ordinal):
                self.rejected("a/" + chr(ordinal), FIELD_MESSAGE, packet_format=True)
        portable_cases = ("a" * 221, "a" * 4096, ".a", "-a", "_a", "/a", "C:/a", "a\\b",
                          "a b", "a/é", "a/中", "a/\u0301", "a/\x7f", "a?b", "a|b", "a<b", "a\"b",
                          "CON/" + "a" * 217)
        for value in portable_cases:
            with self.subTest(value=repr(value)[:80]):
                self.rejected(value, PORTABLE_MESSAGE, packet_format=True)

    def test_normalization_and_multi_issue_diagnostic_order_is_preserved(self):
        cases = (("a//b", NORMALIZED_MESSAGE), ("a/./b", NORMALIZED_MESSAGE),
                 ("a/../b", NORMALIZED_MESSAGE), ("a/", NORMALIZED_MESSAGE),
                 ("CON/..", NORMALIZED_MESSAGE), ("a./../CON", NORMALIZED_MESSAGE),
                 ("a//CON.", NORMALIZED_MESSAGE), ("a.", FILESYSTEM_MESSAGE),
                 ("a/...", FILESYSTEM_MESSAGE), ("a/CON.", FILESYSTEM_MESSAGE),
                 ("a./CON", FILESYSTEM_MESSAGE), ("CON/a.", DEVICE_MESSAGE),
                 ("AUX.json/a./..", NORMALIZED_MESSAGE), ("a/NUL.txt/b.", DEVICE_MESSAGE))
        for value, message in cases:
            with self.subTest(value=value):
                self.rejected(value, message)
        self.rejected("a/../b", NORMALIZED_MESSAGE, at="manifest.evidence.source.path")

    def test_all_legacy_reserved_stems_case_and_extensions_remain_rejected(self):
        stems = ("CON", "PRN", "AUX", "NUL") + tuple("COM%d" % number for number in range(1, 10)) + tuple(
            "LPT%d" % number for number in range(1, 10))
        for stem in stems:
            for value in (stem, stem.lower(), stem + ".json", "nested/" + stem.lower() + ".backup.txt"):
                with self.subTest(value=value):
                    self.rejected(value, DEVICE_MESSAGE)

    def test_actual_checkpoint_and_packet_io_keep_wrapper_diagnostics(self):
        checkpoint = fixture(self.root / "inputs")
        original = packet.canonical(checkpoint)
        self.assertIsNone(contracts.validate_checkpoint(checkpoint))
        self.assertEqual(packet.canonical(checkpoint), original)
        malformed = copy.deepcopy(checkpoint)
        malformed["evidence"]["owner"]["path"] = "CON/.."
        with self.assertRaises(contracts.ContractError) as caught:
            contracts.validate_checkpoint(malformed)
        self.assertEqual((caught.exception.code, str(caught.exception)),
                         ("INVALID_PATH", "checkpoint.evidence.owner.path must be a normalized relative POSIX path"))
        with self.assertRaises(contracts.ContractError) as caught:
            packet.seal(self.root / "rejected-store", malformed, self.root / "inputs")
        self.assertEqual((caught.exception.code, str(caught.exception)),
                         ("INVALID_PATH", "checkpoint.evidence.owner.path must be a normalized relative POSIX path"))
        with self.assertRaises(contracts.ContractError) as caught:
            packet._path(self.root, "CON/..")
        self.assertEqual((caught.exception.code, str(caught.exception)), ("unsafe_path", "Unsafe evidence path: CON/.."))
        receipt = self.root / "nested" / "owner.json"
        receipt.parent.mkdir()
        receipt.write_bytes(b'{"original":"retained"}\n')
        self.assertEqual(packet._path(self.root, "nested/owner.json"), receipt)
        self.assertEqual(packet.read_json(receipt), {"original": "retained"})

    def test_generated_and_checked_in_packets_match_pre_extraction_byte_hashes(self):
        inputs = self.root / "inputs"
        checkpoint = fixture(inputs)
        examples = Path(__file__).with_name("examples")
        example = packet.read_json(examples / "checkpoint.json")
        self.assertEqual(packet.digest((examples / "checkpoint.json").read_bytes()), EXAMPLE_CHECKPOINT_SHA256)
        cases = (("generated", checkpoint, inputs, FIXTURE_CHECKPOINT_SHA256, FIXTURE_PACKET_SHA256, FIXTURE_POINTER_SHA256),
                 ("checked-in", example, examples, EXAMPLE_CHECKPOINT_SHA256, EXAMPLE_PACKET_SHA256, EXAMPLE_POINTER_SHA256))
        for label, doc, evidence, checkpoint_hash, manifest_hash, pointer_hash in cases:
            with self.subTest(source=label):
                original = packet.canonical(doc)
                self.assertEqual(packet.digest(original), checkpoint_hash)
                self.assertIsNone(contracts.validate_checkpoint(doc))
                originals = {row["path"]: (evidence / row["path"]).read_bytes()
                             for row in doc["evidence"].values() if row["status"] == "present"}
                store = self.root / (label + "-store")
                published = packet.seal(store, doc, evidence)
                self.assertEqual(published["sha256"], manifest_hash)
                manifest = store / "packets" / manifest_hash / "manifest.json"
                self.assertEqual(packet.digest(manifest.read_bytes()), manifest_hash)
                self.assertEqual(packet.digest((store / "current.json").read_bytes()), pointer_hash)
                opened = packet.read_packet(store)
                self.assertEqual(opened["sha256"], manifest_hash)
                self.assertEqual(packet.canonical(opened["checkpoint"]), original)
                for name, raw in originals.items():
                    self.assertEqual((evidence / name).read_bytes(), raw)
                    self.assertEqual((store / "packets" / manifest_hash / "evidence" / name).read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
