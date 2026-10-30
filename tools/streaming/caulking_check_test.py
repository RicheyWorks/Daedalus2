# SPDX-License-Identifier: MIT
"""Tests for caulking_check (G544)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caulking_check as cc  # noqa: E402

HOOK = os.path.join(cc.ROOT, "data", "islands", "disk-saver", "caulking-check-v1.json")


def kinds(fs):
    return sorted(x["kind"] for x in fs)


class Repo:
    def __init__(self, files):
        self.d = tempfile.TemporaryDirectory()
        for n, b in files.items():
            p = os.path.join(self.d.name, *n.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(b)

    def __enter__(self):
        return self.d.name

    def __exit__(self, *a):
        self.d.cleanup()


class CaulkingTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(cc.check_bytes("a.py", b"x = 1\n"), [])
        self.assertEqual(cc.check_bytes("a.json", b'{"a": 1}\n'), [])
        self.assertEqual(cc.check_bytes("e.txt", b""), [])

    def test_bad_utf8(self):
        f = cc.check_bytes("a.md", b"ok\n\xff\xfe\n")
        self.assertEqual(kinds(f), ["bad_utf8"])
        self.assertEqual(f[0]["offset"], 3)

    def test_bom_still_checks_rest(self):
        self.assertEqual(kinds(cc.check_bytes("a.json", cc.BOM + b'{"a": 1}\n')), ["bom"])

    def test_crlf_and_mixed(self):
        f = cc.check_bytes("a.txt", b"a\r\nb\r\n")
        self.assertEqual((f[0]["kind"], f[0]["lines"], f[0]["mixed"]), ("crlf", 2, False))
        self.assertTrue(cc.check_bytes("a.txt", b"a\r\nb\n")[0]["mixed"])

    def test_final_newline(self):
        self.assertEqual(kinds(cc.check_bytes("a.py", b"x = 1")), ["no_final_newline"])

    def test_trailing_space_not_markdown(self):
        f = cc.check_bytes("a.py", b"a = 1\nb = 2  \nc = 3\t\n")
        self.assertEqual((f[0]["lines"], f[0]["first"]), (2, 2))
        self.assertEqual(cc.check_bytes("a.md", b"line  \nnext\n"), [])

    def test_tab_indent(self):
        f = cc.check_bytes("a.yml", b"a:\n\tb: 1\n  \tc: 2\n")
        self.assertEqual((f[0]["kind"], f[0]["lines"]), ("tab_indent", 2))
        self.assertEqual(cc.check_bytes("a.txt", b"\tok\n"), [])

    def test_duplicate_key_nested(self):
        f = cc.check_bytes("a.json", b'{"a": {"b": 1, "b": 2}}\n')
        self.assertEqual((f[0]["kind"], f[0]["detail"]), ("duplicate_key", "b"))

    def test_bad_json_and_jsonl(self):
        self.assertEqual(kinds(cc.check_bytes("a.json", b'{"a": }\n')), ["bad_json"])
        f = cc.check_bytes("a.jsonl", b'{"a": 1}\n\n{"a": 1, "a": 2}\n{oops}\n')
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["kind"], f[0]["line"]), ("duplicate_key", 3))

    def test_survey_walk_skip_and_verdicts(self):
        files = {"lane/a.py": b"x = 1\n", "lane/b.bin": b"\xff", "lane/.hidden/c.py": b"\xff",
                 "lane/__pycache__/d.py": b"\xff", "lane/e.md": b"x"}
        with Repo(files) as root:
            r = cc.survey(root, ("lane",))
            self.assertEqual((r["files"], r["verdict"]), (2, "weeping"))
            with open(os.path.join(root, "lane", "f.json"), "wb") as f:
                f.write(b"{\n")
            self.assertEqual(cc.survey(root, ("lane",))["verdict"], "leaking")
            os.remove(os.path.join(root, "lane", "f.json"))
            os.remove(os.path.join(root, "lane", "e.md"))
            self.assertEqual(cc.survey(root, ("lane", "lane/a.py"))["verdict"], "sound")

    def test_cli(self):
        with Repo({"lane/a.json": b'{"k": 1, "k": 1}\n'}) as root:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cc.main(["--root", root, "--under", "lane", "--json", "--fail-on", "leaking"]), 1)
            self.assertEqual(json.loads(out.getvalue())["format"], cc.FORMAT)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cc.main(["--root", root, "--under", "lane"]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cc.main(["--root", root, "--under", "nope"]), 2)

    def test_deterministic(self):
        with Repo({"l/b.py": b"a \r\n", "l/a.json": b"[1,"}) as root:
            self.assertEqual(json.dumps(cc.survey(root, ("l",))), json.dumps(cc.survey(root, ("l",))))

    def test_real_lane_not_leaking(self):
        self.assertNotEqual(cc.survey(cc.ROOT)["verdict"], "leaking")

    def test_hook_covers_values(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_caulking_check")
        self.assertEqual(h["npc"]["name"], "Caulker Evander")
        self.assertEqual(h["hook"]["values"], ["sound", "weeping", "leaking"])
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
