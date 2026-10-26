# SPDX-License-Identifier: MIT
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import deprecated_editor_api as d  # noqa: E402


class ScanTest(unittest.TestCase):
    def test_finds_calls_and_replacement(self):
        hits = d.scan_text("a.py", "w = unreal.EditorLevelLibrary.get_editor_world()\n")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].method, "get_editor_world")
        self.assertIn("UnrealEditorSubsystem", hits[0].replacement)
        self.assertFalse(hits[0].saves_level)

    def test_flags_saves_and_strings_skips_comments(self):
        text = ("unreal.EditorLevelLibrary.save_current_level()\n"
                "# unreal.EditorLevelLibrary.get_editor_world()\n"
                's = src.replace("unreal.EditorLevelLibrary.save_current_level()", "x")\n')
        hits = d.scan_text("b.py", text)
        self.assertEqual([h.line for h in hits], [1, 3])
        self.assertTrue(all(h.saves_level for h in hits))
        self.assertEqual([h.in_string for h in hits], [False, True])

    def test_subsystem_calls_are_clean(self):
        text = "unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()\n"
        self.assertEqual(d.scan_text("c.py", text), [])

    def test_tree_report_is_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "tools", "islands", "kennel"))
            f = os.path.join(root, "tools", "islands", "kennel", "x.py")
            src = "unreal.EditorLevelLibrary.get_game_world()\n"
            with open(f, "w") as fh:
                fh.write(src)
            out = os.path.join(root, "r.md")
            self.assertEqual(d.main(["--root", root, "--out", out]), 0)
            with open(f) as fh:
                self.assertEqual(fh.read(), src)
            with open(out) as fh:
                report = fh.read()
            self.assertIn("islands/kennel", report)
            self.assertIn("1 call(s) in 1 file(s)", report)
            self.assertEqual(d.main(["--root", root, "--out", out, "--fail-on-hits"]), 1)


if __name__ == "__main__":
    unittest.main()
