# SPDX-License-Identifier: MIT
"""Tests for Pier Register (G534): every finding kind, name checks, real repo register, CLI."""
import io
import json
import os
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import pier_register as pr  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "pier-register-v1.json")


class Repo:
    """A throwaway repo root with hook files, docs and tools."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for d in ("data/islands/disk-saver", "docs/islands", "tools/streaming"):
            os.makedirs(os.path.join(self.root, d))

    def hook(self, slug, doc=None, raw=None, doc_md=True, tool=True):
        path = os.path.join(self.root, "data", "islands", "disk-saver", f"{slug}-v1.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw if raw is not None else json.dumps(doc))
        if doc_md:
            open(os.path.join(self.root, "docs", "islands", f"DISKSAVER-{slug.upper()}.md"), "w").close()
        if tool:
            with open(os.path.join(self.root, "tools", "streaming", slug.replace("-", "_") + ".py"), "w") as f:
                f.write("# tool\n")

    def close(self):
        self.tmp.cleanup()


def good(quest, name, values=("a", "b")):
    return {"v": 1, "quest": quest, "hook": {"values": list(values)},
            "npc": {"name": name, "lines": {v: "line" for v in values}}}


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = pr.main(list(args))
    return code, out.getvalue(), err.getvalue()


class PierRegisterTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def kinds(self):
        return sorted(x["kind"] for x in pr.register(self.repo.root)["findings"])

    def test_registered(self):
        self.repo.hook("sea-one", good("q_sea_one", "Keeper Alba"))
        self.repo.hook("sea-two", good("q_sea_two", "Keeper Brann"))
        r = pr.register(self.repo.root)
        self.assertEqual((r["verdict"], r["findings"], len(r["berths"])), ("registered", [], 2))
        self.assertEqual(r["berths"][0]["doc"], "docs/islands/DISKSAVER-SEA-ONE.md")
        self.assertEqual(r["berths"][0]["tool"], "tools/streaming/sea_one.py")

    def test_bad_json_and_no_quest(self):
        self.repo.hook("broken", raw="{nope")
        self.repo.hook("questless", {"v": 1, "npc": {"name": "A B"}})
        self.repo.hook("badquest", good("Quest Name", "C D"))
        self.assertEqual(self.kinds(), ["bad_json", "no_quest", "no_quest"])
        self.assertEqual(pr.register(self.repo.root)["verdict"], "unregistered")

    def test_report_files_are_skipped(self):
        self.repo.hook("some-baseline", {"format": "daedalus-census-budget", "version": 1}, doc_md=False, tool=False)
        self.assertEqual(pr.register(self.repo.root)["berths"], [])

    def test_duplicate_quest(self):
        self.repo.hook("one", good("q_same", "Keeper Alba"))
        self.repo.hook("two", good("q_same", "Keeper Brann"))
        r = pr.register(self.repo.root)
        self.assertEqual(r["findings"], [{"file": None, "kind": "duplicate_quest", "quest": "q_same",
                                          "files": ["one-v1.json", "two-v1.json"]}])

    def test_lines_must_cover_values(self):
        doc = good("q_x", "Keeper Alba")
        doc["npc"]["lines"]["extra"] = "fine"
        self.repo.hook("x", doc)
        self.assertEqual(self.kinds(), [])
        doc["hook"]["values"].append("c")
        self.repo.hook("x", doc)
        f = pr.register(self.repo.root)["findings"]
        self.assertEqual((f[0]["kind"], f[0]["missing"]), ("lines_mismatch", ["c"]))

    def test_doc_by_quest_name_and_missing(self):
        self.repo.hook("census-budget", good("q_census_beacons", "Pilot Alba"), doc_md=False)
        open(os.path.join(self.repo.root, "docs", "islands", "DISKSAVER-CENSUS-BEACONS.md"), "w").close()
        self.repo.hook("lonely", good("q_lonely", "Keeper Brann"), doc_md=False)
        r = pr.register(self.repo.root)
        self.assertEqual(r["berths"][0]["doc"], "docs/islands/DISKSAVER-CENSUS-BEACONS.md")
        self.assertEqual([x["file"] for x in r["findings"] if x["kind"] == "no_doc"], ["lonely-v1.json"])

    def test_tool_by_prefix_or_mention(self):
        self.repo.hook("tide-chart", good("q_tide_chart", "Keeper Alba"), tool=False)
        with open(os.path.join(self.repo.root, "tools", "streaming", "tide_chart_cache.py"), "w") as f:
            f.write("#\n")
        self.repo.hook("odd", good("q_odd", "Keeper Brann"), tool=False)
        with open(os.path.join(self.repo.root, "tools", "streaming", "other.py"), "w") as f:
            f.write("CONFIG = 'data/islands/disk-saver/odd-v1.json'\n")
        self.repo.hook("none", good("q_none", "Keeper Cato"), tool=False)
        with open(os.path.join(self.repo.root, "tools", "streaming", "none_test.py"), "w") as f:
            f.write("# tests do not count\n")
        r = pr.register(self.repo.root)
        self.assertEqual({b["slug"]: b["tool"] for b in r["berths"]},
                         {"none": None, "odd": "tools/streaming/other.py", "tide-chart": "tools/streaming/tide_chart_cache.py"})

    def test_name_reused_and_no_npc(self):
        self.repo.hook("a", good("q_a", "Keeper Wren"))
        self.repo.hook("b", good("q_b", "Tally Clerk wren"))
        self.repo.hook("c", {"v": 1, "quest": "q_c"})
        self.assertEqual(self.kinds(), ["name_reused", "no_npc"])
        self.assertEqual(pr.register(self.repo.root)["verdict"], "queried")

    def test_name_check(self):
        self.repo.hook("a", good("q_a", "Keeper Wren"))
        reg = pr.register(self.repo.root)
        self.assertFalse(pr.name_check(reg, "Harbour Pilot Wren")["free"])
        self.assertTrue(pr.name_check(reg, "Pier Registrar Abelard")["free"])
        with self.assertRaises(pr.RegisterError):
            pr.name_check(reg, "  ")

    def test_counts_equal_brute_force(self):
        rng = random.Random(534)
        for trial in range(40):
            repo = Repo()
            try:
                quests, names, bad = [], [], 0
                for k in range(rng.randrange(1, 7)):
                    q = rng.choice(["q_a", "q_b", "q_c", "q_d%d" % k])
                    n = "Keeper " + rng.choice(["Alba", "Brann", "Cato", "Dun%d" % k])
                    if rng.random() < 0.15:
                        repo.hook("h%d" % k, raw="[1, 2")
                        bad += 1
                        continue
                    repo.hook("h%d" % k, good(q, n))
                    quests.append(q)
                    names.append(n.split()[-1].lower())
                c = pr.register(repo.root)["counts"]
                self.assertEqual(c["bad_json"], bad)
                self.assertEqual(c["duplicate_quest"], sum(1 for q in set(quests) if quests.count(q) > 1))
                self.assertEqual(c["name_reused"], sum(1 for n in set(names) if names.count(n) > 1))
            finally:
                repo.close()

    def test_real_repo_has_no_errors_and_abelard_is_unique(self):
        r = pr.register(ROOT)
        self.assertEqual(sum(r["counts"][k] for k in pr.ERRORS), 0, r["findings"])
        self.assertTrue(any(b["file"] == "pier-register-v1.json" for b in r["berths"]))
        self.assertEqual([b["npc"] for b in r["berths"] if pr.given(b["npc"]) == "abelard"], ["Pier Registrar Abelard"])
        self.assertFalse(pr.name_check(r, "Someone Wren")["free"])

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["registered", "queried", "unregistered"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))

    def test_cli_exit_codes_and_refusals(self):
        self.repo.hook("a", good("q_a", "Keeper Wren"))
        self.repo.hook("b", good("q_b", "Keeper wren"))
        root = self.repo.root
        self.assertEqual(run_cli("--root", root)[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "unregistered")[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "queried")[0], 1)
        code, out, _ = run_cli("--root", root, "--name", "Pilot Wren")
        self.assertEqual(code, 1)
        self.assertIn("taken by Keeper Wren", out)
        code, out, _ = run_cli("--root", root, "--name", "Pilot Abelard", "--json")
        self.assertEqual((code, json.loads(out)["name_check"]["free"]), (0, True))
        code, _, err = run_cli("--root", os.path.join(root, "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("refused", err)


if __name__ == "__main__":
    unittest.main()
