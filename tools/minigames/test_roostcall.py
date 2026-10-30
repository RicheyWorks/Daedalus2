"""Tests for tools/minigames/roostcall.py (Roostcall)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import roostcall as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def yard(self, size, whistler, birds, turns=10):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, size=size, birds=len(birds), turns=turns)
        g.whistler, g.birds, g.turns, g.settled = list(whistler), [list(b) for b in birds], turns, 0
        return g

    def test_setup(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(9, d)
            self.assertEqual(g.whistler, [0, 0])
            self.assertEqual(len(g.birds), cfg["birds"])
            self.assertEqual(len({tuple(b) for b in g.birds}), cfg["birds"])
            for r, c in g.birds:
                self.assertFalse(g.in_roost(r, c))
                self.assertGreater(max(r, c), gm.SCARE_RANGE, "birds start out of reach")

    def test_bird_flees_directly_away(self):
        g = self.yard(6, (1, 1), [(2, 1)])
        self.assertEqual(g.flee_step(0), [3, 1])          # whistler north: bird goes south
        g = self.yard(6, (2, 3), [(2, 1)])
        self.assertEqual(g.flee_step(0), [2, 0])          # whistler east: bird goes west
        g = self.yard(6, (4, 4), [(1, 1)])
        self.assertIsNone(g.flee_step(0), "out of scare range")

    def test_cornered_bird_slides_along_the_edge(self):
        g = self.yard(6, (0, 4), [(0, 5)])
        self.assertEqual(g.flee_step(0), [1, 5])          # beside a corner bird: it goes down the edge
        g = self.yard(6, (1, 4), [(0, 5)])
        self.assertIsNone(g.flee_step(0), "nothing is strictly farther from a diagonal whistler")

    def test_blocked_bird_sidesteps_or_stays_and_ties_go_in_order(self):
        g = self.yard(6, (1, 1), [(2, 1), (3, 1)])
        self.assertEqual(g.flee_step(0), [2, 2], "the cell behind is taken, so it sidesteps (e before w)")
        self.assertEqual(g.flee_step(1), [4, 1])
        g = self.yard(6, (1, 1), [(2, 1), (3, 1), (2, 2), (2, 0)])
        self.assertIsNone(g.flee_step(0), "boxed in on every farther side")
        g = self.yard(6, (2, 2), [(1, 1)])                # equal escapes north and west: n wins the tie
        self.assertEqual(g.flee_step(0), [0, 1])

    def test_perch_settles_and_wins(self):
        g = self.yard(6, (2, 4), [(3, 4)], turns=5)
        res = g.step("wait")
        self.assertEqual((g.birds, g.settled), ([], 1))
        self.assertTrue(g.won and res.endswith("every bird is home"))
        self.assertEqual(g.score, gm.BIRD_SCORE + 4)

    def test_dusk_loses(self):
        g = self.yard(6, (0, 0), [(5, 0)], turns=1)
        self.assertTrue(g.step("wait").startswith("wait: 0 flew, dusk falls"))
        self.assertTrue(g.over and not g.won and g.score == 0)

    def test_moves_are_checked(self):
        g = self.yard(6, (0, 0), [(0, 1)])
        with self.assertRaises(ValueError):
            g.step("n")
        with self.assertRaises(ValueError):
            g.step("e")
        with self.assertRaises(ValueError):
            g.step("x")

    def test_demo_herds_every_seed_home_given_time(self):
        import io
        for d in gm.DIFFICULTY:
            gm.DIFFICULTY[d] = dict(gm.DIFFICULTY[d], turns=300)
            try:
                for s in range(40):
                    self.assertTrue(gm.demo(s, d, io.StringIO()).won, f"{d} seed {s}")
            finally:
                gm.DIFFICULTY[d] = dict(gm.DIFFICULTY[d], turns={"easy": 16, "normal": 30, "hard": 48}[d])


if __name__ == "__main__":
    unittest.main()


class Properties(unittest.TestCase):
    """Iteration 1: invariants on every yard, every move, every seed (no rule change)."""
    SEEDS = range(60)

    def check(self, g, before):
        s = g.size()
        self.assertEqual(g.turns, before["turns"] - 1, "every action is one turn")
        self.assertEqual(g.settled + len(g.birds), g.cfg["birds"], "birds are home or in the yard, never lost")
        self.assertEqual(len({tuple(b) for b in g.birds}), len(g.birds), "no two birds share a cell")
        self.assertNotIn(g.whistler, g.birds, "the whistler never shares a cell with a bird")
        self.assertTrue(all(0 <= r < s and 0 <= c < s for r, c in g.birds + [g.whistler]))
        self.assertTrue(all(not g.in_roost(r, c) for r, c in g.birds), "a bird in the roost has perched")
        self.assertLessEqual(abs(g.whistler[0] - before["whistler"][0]) + abs(g.whistler[1] - before["whistler"][1]), 1)
        self.assertEqual(g.over, not g.birds or g.turns <= 0, "the yard ends exactly when all are home or at dusk")
        self.assertEqual(g.won, not g.birds)
        if g.over:
            self.assertEqual(g.score, gm.BIRD_SCORE * g.settled + (g.turns if g.won else 0))
        else:
            self.assertEqual(g.score, 0)

    def legal_moves(self, g):
        s = g.size()
        return [n for n, (dr, dc) in gm.MOVES.items()
                if 0 <= g.whistler[0] + dr < s and 0 <= g.whistler[1] + dc < s and [g.whistler[0] + dr, g.whistler[1] + dc] not in g.birds]

    def snapshot(self, g):
        return {"turns": g.turns, "whistler": list(g.whistler)}

    def test_random_legal_moves_keep_invariants(self):
        import random
        for d in gm.DIFFICULTY:
            for seed in self.SEEDS:
                g = gm.start(seed, d)
                rng = random.Random(seed * 17 + 3)
                while not g.over:
                    before = self.snapshot(g)
                    g.step(rng.choice(self.legal_moves(g)))
                    self.check(g, before)

    def test_demo_moves_keep_invariants_and_are_legal(self):
        for d in gm.DIFFICULTY:
            for seed in self.SEEDS:
                g = gm.start(seed, d)
                while not g.over:
                    before = self.snapshot(g)
                    a = g.demo_action()
                    self.assertIn(a, self.legal_moves(g))
                    g.step(a)
                    self.check(g, before)

    def test_birds_never_step_closer(self):
        for seed in self.SEEDS:
            g = gm.start(seed, "hard")
            while not g.over:
                a = g.demo_action()
                dr, dc = gm.MOVES[a]
                w = [g.whistler[0] + dr, g.whistler[1] + dc]
                before = {tuple(b): max(abs(b[0] - w[0]), abs(b[1] - w[1])) for b in g.birds}
                moved_from = {}
                for i, b in enumerate(g.birds):
                    to = g.flee_step(i, w)
                    if to is not None:
                        moved_from[tuple(to)] = tuple(b)
                g.step(a)
                for b in g.birds:
                    src = moved_from.get(tuple(b))
                    if src is not None:
                        self.assertGreater(max(abs(b[0] - w[0]), abs(b[1] - w[1])) * 10 + abs(b[0] - w[0]) + abs(b[1] - w[1]),
                                           before[src] * 10 + abs(src[0] - w[0]) + abs(src[1] - w[1]), "a fleeing bird ends strictly farther")


class Balance(unittest.TestCase):
    """Iteration 3: the greedy watcher's win rate per difficulty is pinned to a band."""
    BANDS = {"easy": (0.65, 0.92), "normal": (0.55, 0.88), "hard": (0.55, 0.88)}

    def test_greedy_win_rate_bands(self):
        import io
        for d, (lo, hi) in self.BANDS.items():
            wins = sum(gm.demo(s, d, io.StringIO()).won for s in range(100))
            self.assertTrue(lo <= wins / 100 <= hi, f"{d}: greedy wins {wins}/100, band {lo}-{hi}")

    def test_yards_are_not_trivial(self):
        import io
        for d in gm.DIFFICULTY:
            used = [gm.DIFFICULTY[d]["turns"] - gm.demo(s, d, io.StringIO()).turns for s in range(100)]
            self.assertGreaterEqual(sum(used) / 100, 10, f"{d}: average yard too short")
