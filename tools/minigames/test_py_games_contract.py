"""Guard: every pure-Python minigame is covered by the shared contract tests.

minigame_catalog.PY_GAMES lists the stdlib rules modules. Each one must have tools/minigames/test_<id>.py, and that
file must run prism_testkit.GameContract against the module (start state, difficulty table, deterministic demos,
save/load, ...), unless it is listed in CONTRACT_EXEMPT with the reason. The catalog's python_games "tests" entries
must name files that exist. Stdlib unittest; reads source text only, imports none of the games.
"""
import json
import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Modules that predate the shared contract and keep their own tests. Remove an entry once its test uses GameContract.
CONTRACT_EXEMPT = {
    "prism_shard": "first Prismheart game; test_prism_shard.py and test_prism_shard_web.py predate prism_testkit",
}


def py_games():
    text = (HERE / "minigame_catalog.py").read_text(encoding="utf-8")
    m = re.search(r"^PY_GAMES\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not m:
        raise AssertionError("PY_GAMES not found in minigame_catalog.py")
    return re.findall(r"[\"']([a-z0-9_]+)[\"']", m.group(1))


def uses_contract(test_text, mod):
    """The test imports prism_testkit, mixes GameContract into a class, and sets MOD to the module (or its alias)."""
    if not re.search(r"^\s*(?:import prism_testkit\b|from prism_testkit import)", test_text, re.M):
        return False
    if not re.search(r"class \w+\([^)]*GameContract[^)]*\)", test_text):
        return False
    names = {mod} | set(re.findall(rf"^\s*import {re.escape(mod)} as (\w+)", test_text, re.M))
    return any(re.search(rf"^\s*MOD\s*=\s*{re.escape(n)}\s*(?:#.*)?$", test_text, re.M) for n in names)


class Contract(unittest.TestCase):
    def test_py_games_parsed(self):
        games = py_games()
        self.assertTrue(games)
        self.assertEqual(len(games), len(set(games)), "PY_GAMES lists a module twice")

    def test_every_module_and_test_exists(self):
        for mod in py_games():
            self.assertTrue((HERE / f"{mod}.py").is_file(), f"{mod}.py is in PY_GAMES but missing")
            self.assertTrue((HERE / f"test_{mod}.py").is_file(), f"{mod} has no test_{mod}.py")

    def test_every_module_runs_the_shared_contract(self):
        missing = []
        for mod in py_games():
            if mod in CONTRACT_EXEMPT:
                continue
            path = HERE / f"test_{mod}.py"
            if path.is_file() and not uses_contract(path.read_text(encoding="utf-8"), mod):
                missing.append(mod)
        self.assertEqual(missing, [], "these tests do not run prism_testkit.GameContract (or add to CONTRACT_EXEMPT)")

    def test_exemptions_are_live(self):
        games = set(py_games())
        for mod in CONTRACT_EXEMPT:
            self.assertIn(mod, games, f"CONTRACT_EXEMPT names '{mod}', which is not in PY_GAMES")
            text = (HERE / f"test_{mod}.py").read_text(encoding="utf-8")
            self.assertFalse(uses_contract(text, mod), f"test_{mod}.py now uses GameContract; drop the exemption")

    def test_catalog_test_files_exist(self):
        catalog = json.loads((ROOT / "docs/minigames/catalog.json").read_text(encoding="utf-8"))
        for g in catalog.get("python_games", []):
            for t in g.get("tests", []):
                self.assertTrue((HERE / t).is_file(), f"python game '{g.get('id')}' lists missing test {t}")

    def test_uses_contract_detector(self):
        good = ("import prism_testkit\nimport facetlock\n"
                "class C(prism_testkit.GameContract, unittest.TestCase):\n    MOD = facetlock\n")
        self.assertTrue(uses_contract(good, "facetlock"))
        self.assertTrue(uses_contract(good.replace("import prism_testkit", "from prism_testkit import GameContract")
                                      .replace("prism_testkit.GameContract", "GameContract"), "facetlock"))
        aliased = ("import facetlock as gm  # noqa: E402\nimport prism_testkit as kit  # noqa: E402\n"
                   "class Contract(kit.GameContract, unittest.TestCase):\n    MOD = gm\n")
        self.assertTrue(uses_contract(aliased, "facetlock"))
        self.assertFalse(uses_contract(aliased, "lumenpath"))
        self.assertFalse(uses_contract(good, "lumenpath"))
        self.assertFalse(uses_contract(good.replace("GameContract", "Other"), "facetlock"))
        self.assertFalse(uses_contract(good.replace("import prism_testkit\n", ""), "facetlock"))
        self.assertFalse(uses_contract(good.replace("MOD = facetlock", "MOD = facetlock_two"), "facetlock"))


if __name__ == "__main__":
    unittest.main()
