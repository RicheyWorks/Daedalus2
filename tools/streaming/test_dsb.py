# SPDX-License-Identifier: MIT
"""Offline tests: Python port vs the C++/Java parity file, and the manifest generator. Run: python -m unittest tools/streaming/test_dsb.py"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsb  # noqa: E402
import dsb_manifest  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PARITY = os.path.join(ROOT, "engines", "unreal", "core-test", "streaming_budget_parity.txt")


def unescape(s):
    return s.replace("\\r", "\r").replace("\\t", "\t").replace("\\n", "\n")


def flags(b):
    return [c == "1" for c in b]


class ParityTest(unittest.TestCase):
    def test_python_matches_cpp_and_java_parity_file(self):
        cases = picks = bads = 0
        m = None
        with open(PARITY, encoding="utf-8", newline="") as f:
            for line in f.read().split("\n"):
                if line.startswith("raw\t"):
                    m = dsb.parse(unescape(line[4:]))
                elif line.startswith("canon\t"):
                    want = unescape(line[6:])
                    self.assertEqual(dsb.write(m), want)
                    self.assertEqual(dsb.write(dsb.parse(want)), want)
                    cases += 1
                elif line.startswith("pick "):
                    left, want = line.split(" = ")
                    p = left.split(" ")
                    res, ram, disk, count = dsb.pick(m, int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5]), flags(p[6]))
                    self.assertEqual(f"{ram} {disk} {count} {dsb.bits(res)}", want, line)
                    picks += 1
                elif line.startswith("bad\t"):
                    p = line.split("\t")
                    with self.assertRaises(dsb.DsbError) as cm:
                        dsb.parse(unescape(p[1]))
                    self.assertEqual(str(cm.exception), p[2])
                    bads += 1
        self.assertEqual((cases, picks, bads), (40, 240, 17))


class GeneratorTest(unittest.TestCase):
    def make_root(self, layouts, extra=None):
        d = tempfile.mkdtemp()
        for name, doc in layouts.items():
            os.makedirs(os.path.join(d, "data", "islands", name))
            with open(os.path.join(d, "data", "islands", name, "layout.json"), "w") as f:
                json.dump(doc, f)
        os.makedirs(os.path.join(d, "data", "islands"), exist_ok=True)
        if extra is not None:
            with open(os.path.join(d, "data", "islands", "streaming_extra.json"), "w") as f:
                json.dump(extra, f)
        return d

    def test_estimate_and_canonical_order(self):
        root = self.make_root({"b": {"island": "Zed", "origin_cm": [10, -20, 0], "placements": [{}] * 3},
                               "a": {"island": "Alpha", "origin_cm": [0, 0, 0], "placements": []}})
        text, skipped = dsb_manifest.build(root)
        self.assertEqual(skipped, [])
        self.assertEqual(text, "DSB 1\nisland Alpha x 0 y 0 ram 16384 disk 4096\nisland Zed x 10 y -20 ram 16456 disk 4384\n")

    def test_pinned_cost_extra_island_and_skips(self):
        root = self.make_root({"p": {"island": "Pinned", "origin_cm": [1, 2, 3], "placements": [{}], "streaming": {"ram_kib": 777, "disk_kib": 888}},
                               "n": {"island": "NoOrigin", "placements": []}},
                              {"islands": [{"island": "Far Isle!", "origin_cm": [5.6, 7.4], "placement_count": 10}]})
        text, skipped = dsb_manifest.build(root)
        self.assertEqual(len(skipped), 1)
        self.assertIn("island Far_Isle x 6 y 7 ram 16624 disk 5056\n", text)
        self.assertIn("island Pinned x 1 y 2 ram 777 disk 888\n", text)

    def test_duplicate_ids_refused(self):
        root = self.make_root({"a": {"island": "Same", "origin_cm": [0, 0], "placements": []}},
                              {"islands": [{"island": "Same", "origin_cm": [1, 1], "placement_count": 1}]})
        with self.assertRaises(dsb.DsbError):
            dsb_manifest.build(root)

    def test_repo_manifest_is_valid_and_picks(self):
        text, _ = dsb_manifest.build(ROOT)
        isl = dsb.parse(text)
        self.assertGreaterEqual(len(isl), 4)
        by = {i[0]: i for i in isl}
        self.assertIn("DiskSaver", by)
        ds = by["DiskSaver"]
        res, ram, _, count = dsb.pick(isl, ds[1], ds[2], 100000, 150000, 25000)
        self.assertEqual(count, 1)
        self.assertEqual(ram, ds[3])
        res, _, _, count = dsb.pick(isl, ds[1], ds[2], 100000, 150000, 1)
        self.assertEqual(count, 0)

    def test_check_flag(self):
        root = self.make_root({"a": {"island": "A", "origin_cm": [0, 0], "placements": []}})
        out = os.path.join(root, "m.dsb")
        self.assertEqual(dsb_manifest.main(["--root", root, "-o", out]), 0)
        self.assertEqual(dsb_manifest.main(["--root", root, "--check", out]), 0)
        with open(out, "a") as f:
            f.write("# edited\n")
        self.assertEqual(dsb_manifest.main(["--root", root, "--check", out]), 1)


if __name__ == "__main__":
    unittest.main()
