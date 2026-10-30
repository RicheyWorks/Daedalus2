# SPDX-License-Identifier: MIT
"""Engine-free tests for pin_transition.py with synthetic receipts and pins in a temp folder."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pin_transition as pt  # noqa: E402
from pin_transition import br  # noqa: E402


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


class PinTransitionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.plugin = os.path.join(self.tmp, "live", "DaedalusLink")
        self.dll = os.path.join(self.plugin, "Binaries", "Win64", "UnrealEditor-DaedalusLink.dll")
        self.scratch = os.path.join(self.tmp, "scratch")
        os.makedirs(self.scratch)
        self.receipt = os.path.join(self.tmp, "run", "build-receipt.json")
        self.write_receipt({"Source/A.cpp": h("a2"), "Source/B.h": h("b1")}, h("dll2"))
        self.pins = os.path.join(self.tmp, "guards", "protected-files.json")
        self.write_pins(self.pins, [
            {"path": os.path.join(self.plugin, "Source", "A.cpp"), "sha256": h("a1")},
            {"path": os.path.join(self.plugin, "Source", "B.h"), "sha256": h("b1")},
            {"path": self.dll, "sha256": h("dll1")},
            {"path": os.path.join(self.plugin, "Source", "Gone.cpp"), "sha256": h("g")},
            {"path": os.path.join(self.tmp, "elsewhere.txt"), "sha256": h("x")}])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_receipt(self, files, dll_sha):
        receipt = {"schema": br.SCHEMA, "repo": {"head": "abc123"}, "plugin": self.plugin,
                   "files": [{"path": p, "sha256": s} for p, s in sorted(files.items())],
                   "dll": {"path": self.dll, "sha256": dll_sha}}
        data = br.canonical(receipt)
        put(self.receipt, data)
        put(self.receipt + ".sha256", ("%s  build-receipt.json\n" % hashlib.sha256(data).hexdigest()).encode())

    def write_pins(self, path, rows):
        put(path, json.dumps(rows, indent=1).encode())

    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pt.main(list(argv))
        return code, buf.getvalue()

    def propose(self, out="p.json", pins=None):
        out = os.path.join(self.scratch, out)
        args = ["propose", "--receipt", self.receipt, "--out", out]
        for p in pins or [self.pins]:
            args += ["--pins", p]
        code, text = self.run_cli(*args)
        return code, text, out

    def test_proposal_lists_transitions_and_unresolved_without_touching_pins(self):
        before = open(self.pins, "rb").read()
        code, _, out = self.propose()
        self.assertEqual(code, 0)
        self.assertEqual(open(self.pins, "rb").read(), before)
        prop = json.load(open(out))
        self.assertEqual(prop["schema"], pt.SCHEMA)
        f = prop["pins_files"][0]
        self.assertEqual(f["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(f["checked"], 3)
        self.assertEqual(f["outside_plugin"], 1)
        self.assertEqual(len(f["unresolved"]), 1)
        self.assertTrue(f["unresolved"][0].endswith("Gone.cpp"))
        moves = {os.path.basename(t["path"]): (t["from_sha256"], t["to_sha256"]) for t in f["transitions"]}
        self.assertEqual(moves, {"A.cpp": (h("a1"), h("a2")),
                                 "UnrealEditor-DaedalusLink.dll": (h("dll1"), h("dll2"))})
        self.assertEqual(prop["summary"], {"pins_files": 1, "transitions": 2, "unresolved": 1})
        side = open(out + ".sha256").read().split()[0]
        self.assertEqual(side, hashlib.sha256(open(out, "rb").read()).hexdigest())

    def test_check_valid_then_stale_on_any_change(self):
        code, _, out = self.propose()
        self.assertEqual(self.run_cli("check", "--proposal", out)[0], 0)
        rows = json.load(open(self.pins))
        rows[0]["sha256"] = h("a2")
        self.write_pins(self.pins, rows)
        code, text = self.run_cli("check", "--proposal", out)
        self.assertEqual(code, 1)
        self.assertIn("STALE", text)

    def test_check_stale_on_receipt_change_or_tampered_proposal(self):
        _, _, out = self.propose("a.json")
        self.write_receipt({"Source/A.cpp": h("a3"), "Source/B.h": h("b1")}, h("dll2"))
        self.assertEqual(self.run_cli("check", "--proposal", out)[0], 1)
        self.write_receipt({"Source/A.cpp": h("a2"), "Source/B.h": h("b1")}, h("dll2"))
        _, _, out2 = self.propose("b.json")
        data = open(out2, "rb").read().replace(b"abc123", b"abc124")
        put(out2, data)
        code, text = self.run_cli("check", "--proposal", out2)
        self.assertEqual(code, 1)
        self.assertIn("sidecar", text)

    def test_refusals_and_bad_inputs(self):
        before = open(self.pins, "rb").read()
        code, _ = self.run_cli("propose", "--receipt", self.receipt, "--pins", self.pins, "--out", self.pins)
        self.assertEqual(code, 1)
        self.assertEqual(open(self.pins, "rb").read(), before)
        inside = os.path.join(self.plugin, "p.json")
        self.assertEqual(self.run_cli("propose", "--receipt", self.receipt, "--pins", self.pins,
                                      "--out", inside)[0], 1)
        self.assertFalse(os.path.exists(inside))
        _, _, out = self.propose("dup.json")
        first = open(out, "rb").read()
        self.assertEqual(self.propose("dup.json")[0], 1)
        self.assertEqual(open(out, "rb").read(), first)
        put(self.receipt + ".sha256", b"0" * 64 + b"  build-receipt.json\n")
        self.assertEqual(self.propose("bad.json")[0], 3)
        self.assertFalse(os.path.exists(os.path.join(self.scratch, "bad.json")))
        self.assertEqual(self.run_cli("check", "--proposal", os.path.join(self.scratch, "none.json"))[0], 2)

    def test_multiple_pins_files_and_parity_dict_rows(self):
        other = os.path.join(self.tmp, "packaging", "parity.json")
        put(other, json.dumps({"files": [{"path": os.path.join(self.plugin, "Source", "B.h"), "sha256": h("b0")}],
                               "binary": {"path": self.dll, "sha256": h("dll2")}}).encode())
        code, _, out = self.propose("multi.json", [self.pins, other])
        self.assertEqual(code, 0)
        prop = json.load(open(out))
        self.assertEqual(prop["summary"]["pins_files"], 2)
        second = prop["pins_files"][1]
        self.assertEqual(second["checked"], 2)
        self.assertEqual([os.path.basename(t["path"]) for t in second["transitions"]], ["B.h"])
        self.assertEqual(prop["summary"]["transitions"], 3)
        self.assertEqual(self.run_cli("check", "--proposal", out)[0], 0)


if __name__ == "__main__":
    unittest.main()