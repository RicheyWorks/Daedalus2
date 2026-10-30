# SPDX-License-Identifier: MIT
"""Tests for watchfires (G555)."""
import contextlib
import io
import itertools
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import watchfires as wf  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "watchfires-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": 0} for s in slots]} for w, slots in worlds]}


DOC = census([("alpha", [1, 2, 3, 4]), ("beta", [1, 5, 9]), ("gamma", [2, 3, 7, 8])])


def brute(n, edges):
    nb = wf.closed_neighbourhoods(n, edges)
    full = (1 << n) - 1
    for k in range(1, n + 1):
        for c in itertools.combinations(range(n), k):
            lit = 0
            for v in c:
                lit |= nb[v]
            if lit == full:
                return k
    return n


def connected(n, edges):
    seen, stack = {0}, [0]
    adj = {i: set() for i in range(n)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    while stack:
        for v in adj[stack.pop()]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == n


class WatchfiresTest(unittest.TestCase):
    def test_chart_shape(self):
        labels, edges = wf.chart(DOC, 0)
        self.assertEqual(len(labels), 11)
        idx = {l: i for i, l in enumerate(labels)}
        for w, slots in (("alpha", [1, 2, 3, 4]), ("gamma", [2, 3, 7, 8])):
            for a, b in zip(slots, slots[1:]):
                p = tuple(sorted((idx[f"{w}:{a}"], idx[f"{w}:{b}"])))
                self.assertIn(p, edges)
        self.assertTrue(all(a < b for a, b in edges))
        self.assertEqual(len(edges), len(set(edges)))

    def test_chart_connected_and_seeded(self):
        for s in range(15):
            labels, edges = wf.chart(DOC, s)
            self.assertTrue(connected(len(labels), edges), s)
        self.assertEqual(wf.chart(DOC, 4), wf.chart(DOC, 4))
        self.assertGreater(len({json.dumps(wf.chart(DOC, s)[1]) for s in range(10)}), 3)

    def test_par_matches_brute(self):
        for s in range(15):
            labels, edges = wf.chart(DOC, s)
            k, best = wf.par(len(labels), edges)
            self.assertEqual(k, brute(len(labels), edges), s)
            self.assertEqual(len(best), k)

    def test_par_on_random_graphs(self):
        rng = random.Random(3)
        for _ in range(40):
            n = rng.randint(1, 9)
            edges = sorted({tuple(sorted(rng.sample(range(n), 2))) for _ in range(rng.randint(0, 12))} if n > 1 else set())
            self.assertEqual(wf.par(n, edges)[0], brute(n, edges))

    def test_greedy_covers_and_never_beats_par(self):
        for s in range(15):
            labels, edges = wf.chart(DOC, s)
            g = wf.greedy(len(labels), edges)
            nb = wf.closed_neighbourhoods(len(labels), edges)
            lit = 0
            for v in g:
                lit |= nb[v]
            self.assertEqual(lit, (1 << len(labels)) - 1)
            self.assertGreaterEqual(len(g), wf.par(len(labels), edges)[0])

    def test_greedy_trap_exists(self):
        # a hub touching four islands lures greedy, but two leaves of a double star do better
        edges = [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6), (4, 7), (5, 7), (6, 7), (4, 8), (5, 8), (6, 8)]
        found = False
        rng = random.Random(11)
        for _ in range(400):
            n = rng.randint(5, 10)
            es = sorted({tuple(sorted(rng.sample(range(n), 2))) for _ in range(rng.randint(n, 2 * n))})
            if len(wf.greedy(n, es)) > wf.par(n, es)[0]:
                found = True
                break
        self.assertTrue(found, "greedy should sometimes need more fires than par")
        self.assertLessEqual(wf.par(9, edges)[0], len(wf.greedy(9, edges)))

    def test_verdicts(self):
        r = wf.game(DOC, 2, auto=True)
        self.assertEqual((r["verdict"], len(r["fires"])), ("blazing", r["par"]))
        everyone = wf.game(DOC, 2, r["islands"])
        self.assertEqual(everyone["verdict"], "smoky")
        none = wf.game(DOC, 2, [])
        self.assertEqual((none["verdict"], len(none["unlit"])), ("dark", 11))
        dup = wf.game(DOC, 2, r["fires"] + r["fires"])
        self.assertEqual(dup["verdict"], "blazing")

    def test_refusals(self):
        with self.assertRaises(wf.WatchfireError):
            wf.game(DOC, 0, ["omega:1"])
        with self.assertRaises(wf.WatchfireError):
            wf.chart(census([("a", [])]))
        with self.assertRaises(wf.WatchfireError):
            wf.chart(census([("a", list(range(41)))]))
        with self.assertRaises(wf.WatchfireError):
            wf.chart({"format": "nope"})

    def test_tiny_charts(self):
        self.assertEqual(wf.game(census([("a", [1])]), 0, auto=True)["par"], 1)
        two = wf.game(census([("a", [1]), ("b", [1])]), 0, auto=True)
        self.assertEqual((two["par"], two["routes"]), (1, [["a:1", "b:1"]]))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(wf.main([c, "--json"]), 0)
            self.assertNotIn("fires", json.loads(out.getvalue()))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(wf.main([c, "--auto"]), 0)
            self.assertTrue(out.getvalue().startswith("watchfires: blazing"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(wf.main([c, "--fires", "alpha:1"]), 0)
            self.assertIn("dark", out.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(wf.main([c, "--fires", "nowhere:9"]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        r = wf.game(doc, 0, auto=True)
        self.assertEqual((len(r["islands"]), r["par"], r["verdict"]), (3, 1, "blazing"))

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_watchfires")
        self.assertEqual(h["npc"]["name"], "Firekeeper Leofric")
        self.assertEqual(h["hook"]["values"], list(wf.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
