# SPDX-License-Identifier: MIT
"""Tests for fleet_soundings (G551)."""
import contextlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import fleet_soundings as fs  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "fleet-soundings-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 5), (3, 50)]), ("beta", [(4, 300), (5, 0)]), ("gamma", [(6, 2), (7, 0)])])


def brute(size, lengths, rows, cols, hints):
    """All legal moorings by brute force over placement tuples (small cases only)."""
    sols = set()
    per = [fs.placements(size, n) for n in lengths]
    for combo in itertools.product(*per):
        cells = [c for p in combo for c in p]
        if len(set(cells)) != len(cells):
            continue
        ok = True
        for a, b in itertools.combinations(combo, 2):
            if fs._halo(a).intersection(b):
                ok = False
                break
        if not ok:
            continue
        s = frozenset(cells)
        if [sum(1 for r, _ in s if r == i) for i in range(size)] != rows:
            continue
        if [sum(1 for _, c in s if c == i) for i in range(size)] != cols:
            continue
        if all((p in s) == v for p, v in hints.items()):
            sols.add(s)
    return sols


class SoundingsTest(unittest.TestCase):
    def test_ship_lengths(self):
        self.assertEqual([fs.ship_length(n) for n in (0, 1, 9, 10, 99, 100, 5000)], [1, 2, 2, 3, 3, 4, 4])

    def test_fleet_area_capped_and_seeded(self):
        big = census([("w", [(i, 300) for i in range(10)])])
        for s in range(5):
            _, ships = fs.fleet(big, s)
            self.assertLessEqual(sum(n for _, n in ships), fs.MAX_AREA)
        self.assertEqual(fs.fleet(DOC, 2)[1], fs.fleet(DOC, 2)[1])

    def test_solver_matches_brute_force(self):
        size, lengths = 4, [2, 1, 1]
        for seed in range(6):
            p = fs.generate(census([("w", [(1, 3), (2, 0), (3, 0)])]), seed)
            self.assertEqual(p["size"], 6)
        for rows, cols in (([1, 1, 0, 2], [2, 0, 1, 1]), ([2, 0, 1, 1], [1, 1, 0, 2]), ([1, 0, 1, 2], [2, 1, 0, 1])):
            want = brute(size, lengths, rows, cols, {})
            got = set(fs.solve(size, lengths, rows, cols, {}, limit=100))
            self.assertEqual(got, want, (rows, cols))

    def test_generated_puzzles_unique(self):
        for s in range(8):
            p = fs.generate(DOC, s)
            hints = {(h["row"], h["col"]): h["hull"] for h in p["hints"]}
            sols = fs.solve(p["size"], [f["length"] for f in p["fleet"]], p["rows"], p["cols"], hints, limit=3)
            self.assertEqual(len(sols), 1, s)
            hull = {(r, c) for r, row in enumerate(p["solution"]) for c, ch in enumerate(row) if ch == "#"}
            self.assertEqual(set(sols[0]), hull)

    def test_solution_is_charted(self):
        for s in range(5):
            p = fs.generate(DOC, s)
            self.assertEqual(fs.check(p, p["solution"])["verdict"], "charted")

    def test_hints_match_solution(self):
        p = fs.generate(DOC, 1)
        for h in p["hints"]:
            self.assertEqual(p["solution"][h["row"]][h["col"]] == "#", h["hull"])

    def test_reefed(self):
        p = fs.generate(DOC, 0)
        n = p["size"]
        self.assertEqual(fs.check(p, ["." * n] * (n - 1))["verdict"], "reefed")
        self.assertEqual(fs.check(p, ["x" * n] * n)["verdict"], "reefed")
        self.assertEqual(fs.check(p, ["." * n] * n)["verdict"], "reefed")
        bent = ["." * n for _ in range(n)]
        bent[0] = "##" + "." * (n - 2)
        bent[1] = "#." + "." * (n - 2)
        self.assertIn("bent", " ".join(fs.check(p, bent)["problems"]))
        diag = ["." * n for _ in range(n)]
        diag[0] = "#" + "." * (n - 1)
        diag[1] = ".#" + "." * (n - 2)
        self.assertIn("diagonally", " ".join(fs.check(p, diag)["problems"]))

    def test_short_when_legal_but_wrong(self):
        tiny = census([("w", [(1, 0)])])
        p = fs.generate(tiny, 0)
        n = p["size"]
        (r, c), = [(r, c) for r, row in enumerate(p["solution"]) for c, ch in enumerate(row) if ch == "#"]
        moved = ["." * n for _ in range(n)]
        r2, c2 = (r + 2) % n, (c + 3) % n
        moved[r2] = "." * c2 + "#" + "." * (n - c2 - 1)
        self.assertEqual(fs.check(p, moved)["verdict"], "short")

    def test_deterministic(self):
        self.assertEqual(json.dumps(fs.generate(DOC, 4)), json.dumps(fs.generate(DOC, 4)))
        self.assertGreater(len({json.dumps(fs.generate(DOC, s)["solution"]) for s in range(6)}), 2)

    def test_refusals(self):
        with self.assertRaises(fs.SoundingsError):
            fs.generate(census([("w", [])]))
        with self.assertRaises(fs.SoundingsError):
            fs.generate({"format": "nope"})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(fs.main([c, "--json", "--seed", "2"]), 0)
            self.assertNotIn("solution", json.loads(out.getvalue()))
            sol = fs.generate(DOC, 2)["solution"]
            g = os.path.join(d, "grid.txt")
            with open(g, "w", encoding="utf-8") as f:
                f.write("\n".join(sol) + "\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(fs.main([c, "--seed", "2", "--check", g]), 0)
            self.assertEqual(out.getvalue().strip(), "fleet soundings: charted")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(fs.main([c, "--check", os.path.join(d, "missing.txt")]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        p = fs.generate(doc, 0)
        self.assertEqual(sorted(s["length"] for s in p["fleet"]), [1, 1, 2])
        self.assertEqual(fs.check(p, p["solution"])["verdict"], "charted")

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_fleet_soundings")
        self.assertEqual(h["npc"]["name"], "Tugmaster Ignatius")
        self.assertEqual(h["hook"]["values"], list(fs.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
