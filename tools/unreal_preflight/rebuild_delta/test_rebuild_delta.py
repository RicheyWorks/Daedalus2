import os
import subprocess
import tempfile
import unittest

import rebuild_delta as rd


def g(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write(cwd, rel, text):
    path = os.path.join(cwd, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = self.tmp.name
        g(self.r, "init", "-q", "-b", "main")
        g(self.r, "config", "user.email", "t@example.invalid")
        g(self.r, "config", "user.name", "t")
        write(self.r, "engines/unreal/P/Source/A.cpp", "a")
        g(self.r, "add", "-A")
        g(self.r, "commit", "-q", "-m", "base")
        self.base = g(self.r, "rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def merge(self, branch, rel, n):
        g(self.r, "checkout", "-q", "-b", branch)
        write(self.r, rel, branch)
        g(self.r, "add", "-A")
        g(self.r, "commit", "-q", "-m", branch)
        g(self.r, "checkout", "-q", "main")
        g(self.r, "merge", "-q", "--no-ff", branch, "-m", "Merge pull request #%d from x/%s" % (n, branch))

    def test_lists_only_build_input_merges_oldest_first(self):
        self.merge("cpp", "engines/unreal/P/Source/B.cpp", 7)
        self.merge("docs", "docs/x.md", 8)
        self.merge("hdr", "engines/unreal/P/Source/B.h", 9)
        out = rd.delta(self.base, "main", self.r)
        self.assertTrue(out["needs_rebuild"])
        self.assertEqual([c["pr"] for c in out["commits"]], [7, 9])
        self.assertEqual(out["commits"][0]["files"], 1)

    def test_nothing_to_rebuild(self):
        self.merge("docs", "docs/x.md", 8)
        out = rd.delta(self.base, "main", self.r)
        self.assertFalse(out["needs_rebuild"])
        self.assertEqual(out["commits"], [])

    def test_python_outside_build_inputs_ignored(self):
        self.merge("py", "engines/unreal/P/Content/Python/x.py", 3)
        self.assertFalse(rd.delta(self.base, "main", self.r)["needs_rebuild"])

    def test_non_ancestor_refused(self):
        g(self.r, "checkout", "-q", "--orphan", "other")
        write(self.r, "z.txt", "z")
        g(self.r, "add", "-A")
        g(self.r, "commit", "-q", "-m", "other")
        other = g(self.r, "rev-parse", "HEAD")
        g(self.r, "checkout", "-q", "main")
        with self.assertRaises(ValueError):
            rd.delta(other, "main", self.r)


if __name__ == "__main__":
    unittest.main()
