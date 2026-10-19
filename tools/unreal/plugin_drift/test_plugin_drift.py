"""Offline tests for plugin_drift (temp fixtures only, no Unreal, no network)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugin_drift as pd  # noqa: E402


def write(root, rel, data):
    full = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(data)


class PluginDriftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.live = os.path.join(self.tmp.name, "live")
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.live)
        os.makedirs(self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_trees_no_drift(self):
        for r in (self.live, self.repo):
            write(r, "Source/A/Public/A.h", b"#pragma once\n")
        m = pd.build_manifest(self.live, self.repo)
        self.assertFalse(m["drift"])
        self.assertEqual(m["counts"]["identical"], 1)
        self.assertEqual(pd.main(["--live", self.live, "--repo", self.repo]), 0)

    def test_all_categories(self):
        write(self.live, "Source/A/Private/Same.cpp", b"x\n")
        write(self.repo, "Source/A/Private/Same.cpp", b"x\n")
        write(self.live, "Source/A/Private/Eol.cpp", b"a\r\nb\r\n")
        write(self.repo, "Source/A/Private/Eol.cpp", b"a\nb\n")
        write(self.live, "Source/A/Private/Diff.cpp", b"live\n")
        write(self.repo, "Source/A/Private/Diff.cpp", b"repo\n")
        write(self.live, "Source/A/Private/LiveOnly.cpp", b"l\n")
        write(self.repo, "Source/A/Public/MainOnly.h", b"m\n")
        c = pd.build_manifest(self.live, self.repo)["counts"]
        self.assertEqual(c, {"identical": 1, "eol_only": 1, "differing": 1, "live_only": 1, "main_only": 1})

    def test_eol_only_is_not_drift(self):
        write(self.live, "a.h", b"a\r\n")
        write(self.repo, "a.h", b"a\n")
        self.assertFalse(pd.build_manifest(self.live, self.repo)["drift"])

    def test_build_dirs_excluded(self):
        write(self.live, "Binaries/Win64/x.dll", b"\x00bin")
        write(self.live, "Intermediate/Build/y.obj", b"\x00obj")
        m = pd.build_manifest(self.live, self.repo)
        self.assertFalse(m["drift"])
        self.assertEqual(sum(m["counts"].values()), 0)

    def test_outputs_and_exit_code(self):
        write(self.live, "only.cpp", b"1\n")
        j = os.path.join(self.tmp.name, "m.json")
        md = os.path.join(self.tmp.name, "m.md")
        rc = pd.main(["--live", self.live, "--repo", self.repo, "--json", j, "--md", md, "--label", "T"])
        self.assertEqual(rc, 1)
        with open(j, encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertEqual(m["schema"], "plugin-drift/v1")
        self.assertEqual(m["files"]["live_only"][0]["path"], "only.cpp")
        with open(md, encoding="utf-8") as fh:
            self.assertIn("`only.cpp`", fh.read())

    def test_live_tree_not_modified(self):
        write(self.live, "k.cpp", b"k\n")
        before = {f: os.stat(os.path.join(self.live, f)).st_mtime_ns for f in os.listdir(self.live)}
        pd.build_manifest(self.live, self.repo)
        after = {f: os.stat(os.path.join(self.live, f)).st_mtime_ns for f in os.listdir(self.live)}
        self.assertEqual(before, after)

    def test_missing_dir_is_error(self):
        self.assertEqual(pd.main(["--live", os.path.join(self.tmp.name, "nope"), "--repo", self.repo]), 2)


if __name__ == "__main__":
    unittest.main()
