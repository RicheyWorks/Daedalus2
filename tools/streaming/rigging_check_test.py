# SPDX-License-Identifier: MIT
"""Tests for rigging_check (G541)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rigging_check as rc  # noqa: E402

HOOK = os.path.join(rc.ROOT, "data", "islands", "disk-saver", "rigging-check-v1.json")

GOOD = """permissions:
  contents: read
jobs:
  t:
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: '3.10'
      - run: python tools/streaming/x.py
"""


class Repo:
    def __init__(self, files):
        self.d = tempfile.TemporaryDirectory()
        wf = os.path.join(self.d.name, ".github", "workflows")
        os.makedirs(wf)
        for n, t in files.items():
            with open(os.path.join(wf, n), "w", encoding="utf-8") as f:
                f.write(t)

    def __enter__(self):
        return self.d.name

    def __exit__(self, *a):
        self.d.cleanup()


def kinds(r):
    return [(x["kind"], x["workflow"]) for x in r["findings"]]


class RiggingTest(unittest.TestCase):
    def test_taut(self):
        with Repo({"a.yml": GOOD, "b.yml": GOOD}) as root:
            r = rc.survey(root)
        self.assertEqual(r["verdict"], "taut")
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["actions"]["actions/checkout"]["majors"], {"v5": 2})

    def test_unpinned_no_ref_and_branch(self):
        bad = GOOD.replace("checkout@v5", "checkout").replace("setup-python@v6", "setup-python@main")
        with Repo({"a.yml": GOOD, "b.yml": bad}) as root:
            r = rc.survey(root)
        self.assertEqual(r["verdict"], "frayed")
        self.assertEqual(r["counts"]["unpinned"], 2)
        self.assertEqual({x["ref"] for x in r["findings"] if x["kind"] == "unpinned"}, {None, "main"})

    def test_major_drift_dominant(self):
        old = GOOD.replace("checkout@v5", "checkout@v4")
        with Repo({"a.yml": GOOD, "b.yml": GOOD, "c.yml": old}) as root:
            r = rc.survey(root)
        self.assertEqual(kinds(r), [("major_drift", "c.yml")])
        self.assertEqual(r["findings"][0]["repo_major"], "v5")
        self.assertEqual(r["verdict"], "slack")

    def test_drift_tie_goes_newest(self):
        with Repo({"a.yml": GOOD, "b.yml": GOOD.replace("checkout@v5", "checkout@v7")}) as root:
            r = rc.survey(root)
        self.assertEqual(r["actions"]["actions/checkout"]["repo_major"], "v7")
        self.assertEqual(kinds(r), [("major_drift", "a.yml")])

    def test_minor_versions_same_major(self):
        with Repo({"a.yml": GOOD, "b.yml": GOOD.replace("checkout@v5", "checkout@v5.0.1")}) as root:
            self.assertEqual(rc.survey(root)["verdict"], "taut")

    def test_third_party_tag_vs_sha(self):
        t = GOOD + "      - uses: ilammy/msvc-dev-cmd@v1\n      - uses: other/x@" + "a" * 40 + "\n"
        with Repo({"a.yml": t}) as root:
            r = rc.survey(root)
        tp = [x for x in r["findings"] if x["kind"] == "third_party_tag"]
        self.assertEqual([x["action"] for x in tp], ["ilammy/msvc-dev-cmd"])

    def test_python_drift_and_expressions(self):
        t2 = GOOD.replace("'3.10'", '"3.12"')
        t3 = GOOD.replace("'3.10'", "${{ matrix.py }}")
        with Repo({"a.yml": GOOD, "b.yml": GOOD, "c.yml": t2, "d.yml": t3}) as root:
            r = rc.survey(root)
        self.assertEqual(r["python_versions"], {"3.10": 2, "3.12": 1})
        self.assertEqual(kinds(r), [("python_drift", "c.yml")])

    def test_no_permissions(self):
        with Repo({"a.yml": GOOD.replace("permissions:\n  contents: read\n", "")}) as root:
            r = rc.survey(root)
        self.assertEqual(kinds(r), [("no_permissions", "a.yml")])

    def test_job_level_permissions_not_top_level(self):
        t = GOOD.replace("permissions:\n  contents: read\n", "").replace("  t:\n", "  t:\n    permissions: {}\n")
        with Repo({"a.yml": t}) as root:
            self.assertEqual(rc.survey(root)["counts"]["no_permissions"], 1)

    def test_skips_local_docker_and_comments(self):
        t = GOOD + "      - uses: ./local/action\n      - uses: docker://alpine:3\n      # - uses: foo/bar@main\n"
        with Repo({"a.yml": t}) as root:
            self.assertEqual(rc.survey(root)["verdict"], "taut")

    def test_under_scopes_findings_not_tallies(self):
        other = GOOD.replace("tools/streaming", "tools/other").replace("checkout@v5", "checkout")
        with Repo({"a.yml": GOOD, "b.yml": other}) as root:
            r = rc.survey(root, under="tools/streaming")
        self.assertEqual(r["workflows"], ["a.yml"])
        self.assertEqual(r["verdict"], "taut")

    def test_cli_fail_on_and_json(self):
        with Repo({"a.yml": GOOD.replace("checkout@v5", "checkout@master")}) as root:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = rc.main(["--root", root, "--json", "--fail-on", "frayed"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.getvalue())["format"], rc.FORMAT)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rc.main(["--root", root]), 0)

    def test_refuses_missing_dir(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(rc.main(["--root", d]), 2)

    def test_deterministic(self):
        with Repo({"b.yml": GOOD.replace("@v5", ""), "a.yml": GOOD}) as root:
            self.assertEqual(json.dumps(rc.survey(root)), json.dumps(rc.survey(root)))

    def test_real_repo_lane_is_not_frayed(self):
        r = rc.survey(rc.ROOT, under="tools/streaming")
        self.assertNotEqual(r["verdict"], "frayed")
        self.assertIn("rigging-check.yml", r["workflows"])

    def test_hook_covers_values(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["npc"]["name"], "Bosun Thaddeus")
        lines = " ".join(h["npc"]["lines"].values())
        for v in h["hook"]["values"]:
            self.assertIn(v, h["npc"]["lines"])
        for v in ("taut", "slack", "frayed"):
            self.assertIn(v, h["hook"]["values"])
        self.assertTrue(lines)


if __name__ == "__main__":
    unittest.main()