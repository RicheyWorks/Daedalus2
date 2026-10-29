# SPDX-License-Identifier: MIT
"""Tests for Channel Chart (G536): imports, cycles = brute force, run order, coverage gaps, real repo, CLI."""
import io
import itertools
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
import channel_chart as cc  # noqa: E402

HOOK = os.path.join(ROOT, "data", "islands", "disk-saver", "channel-chart-v1.json")


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for d in ("tools/streaming", ".github/workflows", "data/islands/disk-saver"):
            os.makedirs(os.path.join(self.root, d))

    def tool(self, stem, src="", test=True, workflow=True):
        with open(os.path.join(self.root, "tools", "streaming", stem + ".py"), "w", encoding="utf-8") as f:
            f.write(src)
        if test:
            with open(os.path.join(self.root, "tools", "streaming", stem + "_test.py"), "w", encoding="utf-8") as f:
                f.write(f"import {stem}\n")
        if workflow:
            with open(os.path.join(self.root, ".github", "workflows", stem + ".yml"), "w", encoding="utf-8") as f:
                f.write(f"run: python -m unittest tools/streaming/{stem}_test.py\n")

    def data(self, name):
        open(os.path.join(self.root, "data", "islands", "disk-saver", name), "w").close()

    def chart(self):
        return cc.chart(self.root)

    def close(self):
        self.tmp.cleanup()


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cc.main(list(args))
    return code, out.getvalue(), err.getvalue()


def has_cycle_brute(graph):
    nodes = sorted(graph)
    for k in range(1, len(nodes) + 1):
        for combo in itertools.permutations(nodes, k):
            if all(combo[(i + 1) % k] in graph[combo[i]] for i in range(k)):
                return True
    return False


class ChannelChartTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def test_charted(self):
        self.repo.tool("base", "import json\n")
        self.repo.tool("top", "import base\nimport os\n")
        r = self.repo.chart()
        self.assertEqual((r["verdict"], r["findings"]), ("charted", []))
        self.assertEqual(r["run_order"], ["base", "top"])
        rows = {x["tool"]: x for x in r["tools"]}
        self.assertEqual((rows["top"]["imports"], rows["base"]["imported_by"]), (["base"], ["top"]))

    def test_package_imports_and_missing_module(self):
        self.repo.tool("base")
        self.repo.tool("a", "from tools.streaming import base\nimport tools.streaming.ghost\n")
        r = self.repo.chart()
        self.assertEqual({x["tool"]: x["imports"] for x in r["tools"]}["a"], ["base"])
        self.assertEqual([(f["kind"], f["module"]) for f in r["findings"]], [("missing_module", "tools.streaming.ghost")])
        self.assertEqual(r["verdict"], "uncharted")

    def test_cycle_is_an_error(self):
        self.repo.tool("a", "import b\n")
        self.repo.tool("b", "import c\n")
        self.repo.tool("c", "import a\n")
        r = self.repo.chart()
        self.assertEqual(r["findings"], [{"tool": None, "kind": "import_cycle", "tools": ["a", "b", "c"]}])
        self.assertEqual(sorted(r["run_order"]), ["a", "b", "c"])

    def test_self_import_cycle(self):
        self.repo.tool("a", "import a\n")
        self.assertEqual([f["kind"] for f in self.repo.chart()["findings"]], ["import_cycle"])

    def test_cycles_and_order_equal_brute_force(self):
        rng = random.Random(536)
        for _ in range(60):
            n = rng.randrange(1, 6)
            names = ["m%d" % i for i in range(n)]
            graph = {v: {w for w in names if rng.random() < 0.3} for v in names}
            self.assertEqual(bool(cc._cycles(graph)), has_cycle_brute(graph), graph)
            order = cc.run_order(graph)
            self.assertEqual(sorted(order), names)
            if not cc._cycles(graph):
                pos = {v: i for i, v in enumerate(order)}
                self.assertTrue(all(pos[w] < pos[v] for v in graph for w in graph[v]))

    def test_syntax_error(self):
        self.repo.tool("bad", "def (:\n")
        f = self.repo.chart()["findings"]
        self.assertEqual((f[0]["kind"], f[0]["tool"]), ("syntax_error", "bad"))

    def test_no_test_no_workflow(self):
        self.repo.tool("lonely", test=False, workflow=False)
        self.repo.tool("tested", workflow=False)
        kinds = sorted((f["tool"], f["kind"]) for f in self.repo.chart()["findings"])
        self.assertEqual(kinds, [("lonely", "no_test"), ("lonely", "no_workflow"), ("tested", "no_workflow")])

    def test_test_prefix_style(self):
        self.repo.tool("dsb", test=False)
        with open(os.path.join(self.repo.root, "tools", "streaming", "test_dsb.py"), "w") as f:
            f.write("import dsb\n")
        r = self.repo.chart()
        self.assertEqual(r["tools"][0]["test"], "tools/streaming/test_dsb.py")
        self.assertEqual([t["tool"] for t in r["tools"]], ["dsb"])

    def test_external_import_advisory(self):
        self.repo.tool("a", "import numpy\nimport json\nfrom __future__ import annotations\n")
        r = self.repo.chart()
        self.assertEqual([(f["kind"], f["module"]) for f in r["findings"]], [("external_import", "numpy")])
        self.assertEqual(r["verdict"], "shoals")

    def test_data_files_named_or_unnamed(self):
        self.repo.data("named-v1.json")
        self.repo.data("ci-only-v1.json")
        self.repo.data("orphan-v1.json")
        self.repo.tool("a", "P = 'data/islands/disk-saver/named-v1.json'\n")
        with open(os.path.join(self.repo.root, ".github", "workflows", "x.yml"), "a") as f:
            f.write("run: cat data/islands/disk-saver/ci-only-v1.json\n")
        r = self.repo.chart()
        self.assertEqual(r["tools"][0]["data"], ["named-v1.json"])
        self.assertEqual([f["file"] for f in r["findings"] if f["kind"] == "unnamed_data"], ["orphan-v1.json"])

    def test_nothing_is_executed(self):
        marker = os.path.join(self.repo.root, "ran.txt")
        self.repo.tool("boom", f"open({marker!r}, 'w').write('x')\nraise SystemExit(3)\n")
        self.repo.chart()
        self.assertFalse(os.path.exists(marker))

    def test_real_repo_has_no_errors(self):
        r = cc.chart(ROOT)
        self.assertEqual(sum(r["counts"][k] for k in cc.ERRORS), 0, r["findings"])
        rows = {x["tool"]: x for x in r["tools"]}
        self.assertIn("channel_chart", rows)
        self.assertEqual(rows["channel_chart"]["test"], "tools/streaming/channel_chart_test.py")
        self.assertIn("fleet_flags", rows["census_budget"]["imported_by"])
        self.assertLess(r["run_order"].index("census_budget"), r["run_order"].index("fleet_flags"))

    def test_hook_config(self):
        with open(HOOK, encoding="utf-8") as f:
            hook = json.load(f)
        self.assertEqual(hook["hook"]["values"], ["charted", "shoals", "uncharted"])
        self.assertEqual(set(hook["npc"]["lines"]), set(hook["hook"]["values"]))
        self.assertEqual(hook["npc"]["name"], "Chartmaker Isaura")

    def test_cli_exit_codes_and_refusals(self):
        self.repo.tool("a", test=False)
        root = self.repo.root
        self.assertEqual(run_cli("--root", root)[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "uncharted")[0], 0)
        self.assertEqual(run_cli("--root", root, "--fail-on", "shoals")[0], 1)
        code, out, _ = run_cli("--root", root, "--json")
        self.assertEqual(json.loads(out)["verdict"], "shoals")
        code, _, err = run_cli("--root", os.path.join(root, "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("refused", err)


if __name__ == "__main__":
    unittest.main()