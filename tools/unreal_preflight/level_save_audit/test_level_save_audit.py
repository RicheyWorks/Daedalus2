# SPDX-License-Identifier: MIT
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import level_save_audit as la  # noqa: E402

CASES = {
    "blanket.py": "import unreal\nunreal.EditorLevelLibrary.save_all_dirty_levels()\n",
    "bare_current.py": "import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()\n",
    "own_map.py": "import unreal\nles=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)\nles.load_level('/Game/Mine/L_Mine')\nles.save_current_level()\n",
    "world_then_save.py": "import unreal\nles=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)\nles.load_level('/Game/Daedalus/DaedalusWorld')\nles.save_current_level()\n",
    "guarded.py": ("import unreal\nw = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()\n"
                   "if 'DaedalusWorld' in w.get_path_name():\n    raise SystemExit('refuse persistent world')\n"
                   "unreal.EditorLevelLibrary.save_all_dirty_levels()\n"),
    "explicit.py": "import unreal\nunreal.EditorLoadingAndSavingUtils.save_packages([pkg], True)\n",
    "in_string.py": "CODE = '''\nimport unreal\nunreal.EditorLevelLibrary.save_current_level()\n'''\nsend(CODE)\n",
    "comment_only.py": "# unreal.EditorLevelLibrary.save_all_dirty_levels()\nprint(1)\n",
    "nosave.py": "print('hello')\n",
    "test_skipped.py": "unreal.EditorLevelLibrary.save_all_dirty_levels()\n",
    "broken.py": "def x(:\n  unreal.EditorLevelLibrary.save_all_dirty_levels()\n",
}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for n, s in CASES.items():
            (cls.root / "area" / "sub" / n).parent.mkdir(parents=True, exist_ok=True)
            (cls.root / "area" / "sub" / n).write_text(s, encoding="utf-8")
        cls.rows = {Path(r["file"]).name: r for r in la.scan(cls.root)}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def g(self, n):
        return self.rows[n]["grade"]

    def test_grades(self):
        self.assertEqual(self.g("blanket.py"), "HIGH")
        self.assertEqual(self.g("bare_current.py"), "HIGH")
        self.assertEqual(self.g("own_map.py"), "MEDIUM")
        self.assertEqual(self.g("world_then_save.py"), "HIGH")
        self.assertIn("loads DaedalusWorld", self.rows["world_then_save.py"]["calls"][0]["reason"])
        self.assertEqual(self.g("guarded.py"), "LOW")
        self.assertEqual(self.g("explicit.py"), "LOW")
        self.assertEqual(self.g("broken.py"), "HIGH")

    def test_in_string_marked(self):
        c = self.rows["in_string.py"]["calls"][0]
        self.assertTrue(c["in_string"])
        self.assertEqual(c["grade"], "HIGH")

    def test_skips(self):
        for n in ("comment_only.py", "nosave.py", "test_skipped.py"):
            self.assertNotIn(n, self.rows)

    def test_report_and_exit(self):
        out_md = self.root / "r.md"
        rc = la.main(["--root", str(self.root / "area"), "--md", str(out_md), "--json", str(self.root / "r.json")])
        self.assertEqual(rc, 1)
        md = out_md.read_text(encoding="utf-8")
        self.assertIn("HIGH", md)
        self.assertIn("no script was edited", md)
        self.assertNotIn("r.md", md)

    def test_clean_tree_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "ok.py").write_text("import unreal\nunreal.EditorLoadingAndSavingUtils.save_map(w, '/Game/Mine/L')\n")
            self.assertEqual(la.main(["--root", d]), 0)

    def test_reads_only(self):
        before = {p: p.read_bytes() for p in (self.root / "area").rglob("*.py")}
        la.scan(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.root / "area").rglob("*.py")})


if __name__ == "__main__":
    unittest.main()
