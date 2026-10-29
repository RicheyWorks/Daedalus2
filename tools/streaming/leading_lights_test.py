# SPDX-License-Identifier: MIT
"""Tests for leading_lights (G543)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leading_lights as ll  # noqa: E402

HOOK = os.path.join(ll.ROOT, "data", "islands", "disk-saver", "leading-lights-v1.json")


class Repo:
    def __init__(self, files):
        self.d = tempfile.TemporaryDirectory()
        for n, t in files.items():
            p = os.path.join(self.d.name, *n.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(t)

    def __enter__(self):
        return self.d.name

    def __exit__(self, *a):
        self.d.cleanup()


def kinds(r):
    return [(x["kind"], x["target"]) for x in r["findings"]]


TARGET = "# Title\n\n## Second Part\n\n## Second Part\n"


class LightsTest(unittest.TestCase):
    def test_lit(self):
        with Repo({"docs/a.md": "[b](b.md) [up](../tools/x.py) [web](https://example.com) [me](#top)\n# Top\n",
                   "docs/b.md": TARGET, "tools/x.py": ""}) as root:
            r = ll.survey(root)
        self.assertEqual(r["verdict"], "lit")
        self.assertEqual(r["links"], 3)

    def test_broken_is_dark(self):
        with Repo({"docs/a.md": "see [gone](gone.md) and ![img](pic.png)\n"}) as root:
            r = ll.survey(root)
        self.assertEqual(r["verdict"], "dark")
        self.assertEqual(kinds(r), [("broken", "gone.md"), ("broken", "pic.png")])

    def test_anchor_slugs_and_duplicates(self):
        md = "[a](b.md#second-part) [b](b.md#second-part-1) [c](b.md#second-part-2) [d](b.md#TITLE)\n"
        with Repo({"docs/a.md": md, "docs/b.md": TARGET}) as root:
            r = ll.survey(root)
        self.assertEqual(kinds(r), [("missing_anchor", "b.md#second-part-2")])
        self.assertEqual(r["verdict"], "dim")

    def test_slug_rules(self):
        self.assertEqual(ll.slug("G541 Rigging Check (disk-saver)"), "g541-rigging-check-disk-saver")
        self.assertEqual(ll.slug("`code` & [link](x.md)"), "code--link")

    def test_html_anchor(self):
        with Repo({"a.md": '<a name="here"></a>\n[x](#here)\n'}) as root:
            self.assertEqual(ll.survey(root)["verdict"], "lit")

    def test_local_and_outside(self):
        md = "[w](C:\\Users\\x\\a.md) [f](file:///tmp/a) [h](~/a.md) [o](../../elsewhere.md)\n"
        with Repo({"docs/a.md": md}) as root:
            r = ll.survey(root)
        self.assertEqual(r["counts"]["local_path"], 3)
        self.assertEqual(r["counts"]["outside_repo"], 1)
        self.assertEqual(r["verdict"], "dim")

    def test_root_relative_and_encoded(self):
        with Repo({"docs/deep/a.md": "[r](/tools/my%20file.py) [d](/docs)\n", "tools/my file.py": ""}) as root:
            self.assertEqual(ll.survey(root)["verdict"], "lit")

    def test_code_is_ignored(self):
        md = "```\n[x](gone.md)\n```\nuse `[y](gone.md)` here\n~~~\n# Fake\n~~~\n[z](#fake)\n"
        with Repo({"a.md": md}) as root:
            r = ll.survey(root)
        self.assertEqual(kinds(r), [("missing_anchor", "#fake")])

    def test_stale_inline_paths(self):
        md = "`tools/streaming/real.py` `tools/streaming/gone.py` `tools/*.py` `<dir>/x.py` `docs/sub/near.md` `x/y.py`\n"
        with Repo({"docs/a.md": md, "tools/streaming/real.py": "", "docs/docs/sub/near.md": ""}) as root:
            r = ll.survey(root)
        self.assertEqual(kinds(r), [("stale_path", "tools/streaming/gone.py")])

    def test_under_and_skipped_dirs(self):
        files = {"docs/a.md": "[x](gone.md)\n", "tools/b.md": "ok\n", "node_modules/p/c.md": "[x](gone.md)\n",
                 ".git/d.md": "[x](gone.md)\n"}
        with Repo(files) as root:
            self.assertEqual(ll.survey(root, under="tools")["verdict"], "lit")
            r = ll.survey(root)
        self.assertEqual(r["files"], 2)
        self.assertEqual(r["counts"]["broken"], 1)

    def test_cli(self):
        with Repo({"a.md": "[x](gone.md)\n"}) as root:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ll.main(["--root", root, "--json", "--fail-on", "dark"]), 1)
            self.assertEqual(json.loads(out.getvalue())["format"], ll.FORMAT)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ll.main(["--root", root]), 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ll.main(["--root", os.path.join(root, "nope")]), 2)

    def test_deterministic(self):
        with Repo({"b.md": "[x](a.md#q) `tools/z.py`\n", "a.md": "[y](c.md)\n"}) as root:
            self.assertEqual(json.dumps(ll.survey(root)), json.dumps(ll.survey(root)))

    def test_real_lane_lit_enough(self):
        for lane in ("docs/islands", "tools/streaming"):
            self.assertNotEqual(ll.survey(ll.ROOT, under=lane)["verdict"], "dark", lane)

    def test_hook_covers_values(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_leading_lights")
        self.assertEqual(h["npc"]["name"], "Lightkeeper Seraphine")
        self.assertEqual(h["hook"]["values"], ["lit", "dim", "dark"])
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()