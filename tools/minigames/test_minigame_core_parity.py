"""Unit tests for tools/minigames/minigame_core_parity.py (stdlib unittest)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import minigame_core_parity as parity  # noqa: E402


def _tree(root, *, fixture="seed 1\n", cpp=True, include=True, workflow=True, extra_header=False):
    public = root / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public"
    public.mkdir(parents=True)
    (public / "DaedalusShadewatchCore.h").write_text("#pragma once\n", encoding="utf-8")
    desktop = public / "DesktopGames"
    desktop.mkdir()
    (desktop / "DaedalusDesktopSiltlaneCore.h").write_text("#pragma once\n", encoding="utf-8")
    if extra_header:
        (public / "DaedalusKennelCore.h").write_text("#pragma once\n", encoding="utf-8")
    tests = root / "engines/unreal/core-test"
    tests.mkdir()
    if fixture is not None:
        (tests / "shadewatch_parity.txt").write_text(fixture, encoding="utf-8")
    if cpp:
        body = '#include "DaedalusShadewatchCore.h"\n' if include else "int main(){return 0;}\n"
        (tests / "shadewatch_core_test.cpp").write_text(body, encoding="utf-8")
    workflows = root / ".github/workflows"
    workflows.mkdir(parents=True)
    if workflow:
        script = (
            "run: g++ shadewatch_core_test.cpp -o shadewatch_core_test"
            " && ./shadewatch_core_test shadewatch_parity.txt\n"
        )
    else:
        script = "run: echo shadewatch_core_test.cpp shadewatch_parity.txt\n"
        # Names outside a compiling run must not count; this still mentions them.
        # The negative case uses a comment-only workflow instead when workflow is False
        # and a separate test covers a run that does not compile. See test_comment_is_not_a_run.
    (workflows / "engines.yml").write_text(
        "jobs:\n  mesh:\n    steps:\n      - name: shadewatch\n        " + script,
        encoding="utf-8",
    )
    catalog = root / "docs/minigames"
    catalog.mkdir(parents=True)
    (catalog / "catalog.json").write_text(json.dumps({
        "games": [{"id": "siltlane"}, {"id": "shadewatch"}],
        "python_games": [{"id": "spiritkite"}],
    }), encoding="utf-8")


class CoreParity(unittest.TestCase):
    def test_repo_minigame_cores_have_fixture_test_and_ci(self):
        self.assertEqual(parity.check(), [])

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root)
            self.assertEqual(parity.check(root), [])

    def test_missing_fixture_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, fixture=None)
            gaps = parity.check(root)
            self.assertEqual(len(gaps), 1)
            self.assertIn("shadewatch: missing parity fixture", gaps[0])
            self.assertIn("shadewatch_parity.txt", gaps[0])

    def test_empty_fixture_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, fixture="  \n")
            gaps = parity.check(root)
            self.assertIn("shadewatch: parity fixture", gaps[0])
            self.assertIn("empty", gaps[0])

    def test_missing_core_test_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, cpp=False)
            gaps = parity.check(root)
            self.assertTrue(any("missing core test" in g and "shadewatch" in g for g in gaps))

    def test_core_test_must_include_the_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, include=False)
            gaps = parity.check(root)
            self.assertTrue(any("does not include DaedalusShadewatchCore.h" in g for g in gaps))

    def test_comment_is_not_a_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, workflow=False)
            # Replace the run with a comment that names both files.
            wf = root / ".github/workflows/engines.yml"
            wf.write_text(
                "# shadewatch_core_test.cpp shadewatch_parity.txt\n"
                "jobs:\n  mesh:\n    steps:\n      - name: other\n        run: echo ok\n",
                encoding="utf-8",
            )
            gaps = parity.check(root)
            self.assertEqual(len(gaps), 1)
            self.assertIn("no workflow run script compiles shadewatch_core_test.cpp", gaps[0])
            self.assertIn("shadewatch_parity.txt", gaps[0])

    def test_desktop_host_and_uncatalogued_core_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root, extra_header=True)
            self.assertEqual(parity.check(root), [])

    def test_catalog_game_without_a_native_header_is_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _tree(root)
            self.assertEqual(parity.check(root), [])
            self.assertNotIn("siltlane", " ".join(parity.check(root)))
            self.assertNotIn("spiritkite", " ".join(parity.check(root)))


if __name__ == "__main__":
    unittest.main()
