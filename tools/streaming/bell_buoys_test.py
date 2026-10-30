# SPDX-License-Identifier: MIT
"""Tests for Bell Buoys (G538): paths parsing, glob = reference matcher, every finding kind, real repo, CLI."""
import fnmatch
import io
import json
import os
import random
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import bell_buoys as bb  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "bell-buoys-v1.json")


def workflow(paths, run, trigger="pull_request", key="paths"):
    head = "name: X\non:\n  push:\n    branches: [main]\n"
    if paths is not None:
        head += f"  {trigger}:\n    branches: [main]\n    {key}:\n" + "".join(f"      - '{p}'\n" for p in paths)
    else:
        head += f"  {trigger}:\n    branches: [main]\n"
    return head + "jobs:\n  j:\n    steps:\n" + "".join(f"      - run: {r}\n" for r in run)


class Repo:
    def __init__(self, files=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, ".github", "workflows"))
        for f in files:
            self.file(f)

    def file(self, rel, text=""):
        p = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

    def wf(self, name, text):
        self.file(f".github/workflows/{name}", text)

    def audit(self, under=None):
        return bb.audit(self.root, under)

    def close(self):
        self.tmp.cleanup()


def ref_glob(pattern, path):
    """Reference matcher: split on '/'; '**' matches zero or more segments (one or more when it ends
    the pattern after a '/', since 'dir/**' means files inside dir); fnmatch per segment."""
    ps, xs = pattern.split("/"), path.split("/")

    def go(i, j):
        if i == len(ps):
            return j == len(xs)
        if ps[i] == "**":
            first = j + 1 if i == len(ps) - 1 and i > 0 else j
            return any(go(i + 1, k) for k in range(first, len(xs) + 1))
        return j < len(xs) and fnmatch.fnmatchcase(xs[j], ps[i].replace("[", "[[]")) and go(i + 1, j + 1)
    return go(0, 0)


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bb.main(list(args))
    return code, out.getvalue(), err.getvalue()


class BellBuoysTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(["tools/streaming/a.py", "tools/streaming/a_test.py", "data/islands/x-v1.json"])

    def tearDown(self):
        self.repo.close()

    def test_ringing(self):
        self.repo.wf("a.yml", workflow(["tools/streaming/a*.py", "data/islands/**"],
                                       ["python tools/streaming/a.py data/islands/x-v1.json"]))
        r = self.repo.audit()
        self.assertEqual((r["verdict"], r["findings"]), ("ringing", []))
        self.assertEqual(r["workflows"], [{"workflow": "a.yml", "patterns": 2, "inputs_checked": 2}])

    def test_unguarded(self):
        self.repo.wf("a.yml", workflow(["tools/streaming/a.py"], ["python tools/streaming/a.py data/islands/x-v1.json"]))
        r = self.repo.audit()
        self.assertEqual([(f["kind"], f["path"]) for f in r["findings"]], [("unguarded", "data/islands/x-v1.json")])
        self.assertEqual(r["verdict"], "silent")

    def test_missing_file(self):
        self.repo.wf("a.yml", workflow(["tools/**"], ["python tools/streaming/gone.py"]))
        self.assertEqual([f["kind"] for f in self.repo.audit()["findings"]], ["missing_file"])

    def test_stale_pattern_is_muffled(self):
        self.repo.wf("a.yml", workflow(["tools/streaming/a.py", "tools/nowhere/**"], ["python tools/streaming/a.py"]))
        r = self.repo.audit()
        self.assertEqual(([(f["kind"], f["pattern"]) for f in r["findings"]], r["verdict"]),
                         ([("stale_pattern", "tools/nowhere/**")], "muffled"))

    def test_module_and_directory_refs(self):
        self.repo.file("tools/world_census/__init__.py")
        self.repo.file("docs/contracts/tonic-v1/CUE.md")
        self.repo.wf("a.yml", workflow(["tools/world_census/**"], ["python -m tools.world_census x", "cat docs/contracts/tonic-v1"]))
        r = self.repo.audit()
        self.assertEqual([(f["kind"], f["path"]) for f in r["findings"]], [("unguarded", "docs/contracts/tonic-v1")])

    def test_step_names_and_env_vars_ignored(self):
        self.repo.wf("a.yml", workflow(["tools/streaming/a.py"], ["python tools/streaming/a.py \"$RUNNER_TEMP/tools/out.json\""]).replace(
            "    steps:\n", "    steps:\n      - name: mentions tools/streaming/ghost.py\n"))
        self.assertEqual(self.repo.audit()["findings"], [])

    def test_unfiltered_and_paths_ignore(self):
        self.repo.wf("open.yml", workflow(None, ["python tools/streaming/a.py"]))
        self.repo.wf("ign.yml", workflow(["docs/**"], ["python tools/streaming/a.py"], key="paths-ignore"))
        r = self.repo.audit()
        self.assertEqual((r["unfiltered"], r["workflows"], r["verdict"]), (["ign.yml", "open.yml"], [], "ringing"))

    def test_inline_list_and_pull_request_target(self):
        text = ("on:\n  pull_request_target:\n    paths: ['tools/streaming/a.py', \"data/**\"]\n"
                "jobs:\n  j:\n    steps:\n      - run: python tools/streaming/a.py data/islands/x-v1.json\n")
        self.repo.wf("a.yml", text)
        self.assertEqual(self.repo.audit()["findings"], [])

    def test_glob_equals_reference(self):
        rng = random.Random(538)
        segs = ["a", "b", "a.py", "b_test.py", "x-v1.json"]
        pats = ["*", "**", "a*", "*.py", "*_test.py", "a", "x-*.json", "?.py"]
        for _ in range(600):
            path = "/".join(rng.choice(segs) for _ in range(rng.randrange(1, 4)))
            pattern = "/".join(rng.choice(pats + segs) for _ in range(rng.randrange(1, 4)))
            self.assertEqual(bool(bb.glob_re(pattern).match(path)), ref_glob(pattern, path), (pattern, path))

    def test_under_scope(self):
        self.repo.file("tools/other/b.py")
        self.repo.wf("a.yml", workflow(["tools/streaming/a.py"], ["python tools/streaming/a.py"]))
        self.repo.wf("b.yml", workflow(["nothing/**"], ["python tools/other/b.py"]))
        self.assertEqual(self.repo.audit()["verdict"], "silent")
        r = self.repo.audit("tools/streaming/")
        self.assertEqual(([w["workflow"] for w in r["workflows"]], r["verdict"]), (["a.yml"], "ringing"))

    def test_real_repo_streaming_workflows_ring(self):
        r = bb.audit(ROOT, "tools/streaming")
        self.assertEqual(r["verdict"], "ringing", r["findings"])
        self.assertIn("bell-buoys.yml", [w["workflow"] for w in r["workflows"]])

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["ringing", "muffled", "silent"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Buoy-tender Ottoline")

    def test_cli_exit_codes_and_refusals(self):
        self.repo.wf("a.yml", workflow(["tools/streaming/a.py", "zzz/**"], ["python tools/streaming/a.py"]))
        root = self.repo.root
        self.assertEqual(run_cli("--root", root)[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "silent")[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "muffled")[0], 1)
        code, out, _ = run_cli("--root", root, "--json")
        self.assertEqual(json.loads(out)["counts"], {"unguarded": 0, "missing_file": 0, "stale_pattern": 1})
        code, _, err = run_cli("--root", os.path.join(root, "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("refused", err)


if __name__ == "__main__":
    unittest.main()
