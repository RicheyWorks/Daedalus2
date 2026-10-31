"""Tests for tools/minigames/shuntline.py (Shuntline)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shuntline as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def yard(self, train, sidings=2, length=3, moves=20, destinations=None):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, cars=len(train), destinations=destinations or max(train), sidings=sidings, length=length, moves=moves)
        g.train, g.index, g.sidings, g.outbound, g.moves = list(train), 0, [[] for _ in range(sidings)], [], moves
        return g

    def test_setup_is_solvable(self):
        for d, cfg in gm.DIFFICULTY.items():
            for s in range(20):
                g = gm.start(s, d)
                self.assertEqual(len(g.train), cfg["cars"])
                self.assertTrue(all(1 <= v <= cfg["destinations"] for v in g.train))
                self.assertIsNotNone(g._search(), "%s seed %d" % (d, s))

    def test_out_shunt_pull(self):
        g = self.yard([2, 1, 3])
        self.assertEqual(g.actions(), ["out", "s0", "s1"])
        g.step("s0")
        self.assertEqual((g.sidings[0], g.index, g.moves), ([2], 1, 19))
        g.step("out")
        self.assertEqual(g.outbound, [1])
        self.assertEqual(g.actions(), ["out", "s0", "s1", "p0"])
        g.step("p0")
        self.assertEqual(g.outbound, [1, 2])
        res = g.step("out")
        self.assertTrue(g.won)
        self.assertIn("made up", res)
        self.assertEqual(g.score, 3 * gm.GROUP_SCORE + 16 * gm.MOVE_BONUS)

    def test_order_and_length_are_enforced(self):
        g = self.yard([3, 1, 1, 1, 1], sidings=1, length=2)
        g.step("out")                                   # 3 leaves; now every 1 is dead
        self.assertEqual(g.actions(), ["s0"])
        g.step("s0")
        g.step("s0")
        self.assertEqual(g.actions(), [], "siding full, front carriage lower than the last out")
        self.assertTrue(g.over and not g.won)
        self.assertIn("blocked", g.render())
        for bad in ("out", "p0", "s0", "x"):
            with self.assertRaises(Exception):
                g.step(bad)

    def test_shift_ends(self):
        g = self.yard([1, 2], moves=1)
        res = g.step("out")
        self.assertTrue(g.over and not g.won)
        self.assertIn("shift ends", res)
        self.assertEqual(g.score, gm.GROUP_SCORE)

    def test_parse(self):
        self.assertEqual(gm.Game.parse("out"), "out")
        self.assertEqual(gm.Game.parse("S1"), "s1")
        self.assertEqual(gm.Game.parse("p0"), "p0")
        with self.assertRaises(ValueError):
            gm.Game.parse("q2")

    def test_preview_matches_the_move(self):
        for s in range(20):
            g = gm.start(s, "hard")
            while not g.over:
                a = g.demo_action()
                legal, car, leaves = g.preview(a)
                self.assertTrue(legal)
                state = g.to_state()
                self.assertEqual(g.to_state(), state)
                before = len(g.outbound)
                g.step(a)
                self.assertEqual(len(g.outbound) - before, 1 if leaves else 0)
                if leaves:
                    self.assertEqual(g.outbound[-1], car)

    def test_yardmaster_wins_and_naive_rarely_does(self):
        naive_wins = 0
        for s in range(60):
            g = gm.start(s)
            while not g.over:
                g.step(g.demo_action())
            self.assertTrue(g.won, "seed %d" % s)
            h = gm.start(s)
            while not h.over:
                acts = h.actions()
                h.step("out" if "out" in acts else next((x for x in acts if x[0] == "p"), acts[0]))
            naive_wins += h.won
        self.assertLess(naive_wins, 15)

    def test_properties_hold_under_random_moves(self):
        """Iteration 1: random legal moves on 120 trains never break the order, the lengths or the counters."""
        import random
        for s in range(120):
            d = ("easy", "normal", "hard")[s % 3]
            g = gm.start(s, d)
            rng = random.Random(s)
            while not g.over:
                acts = g.actions()
                a = acts[rng.randrange(len(acts))]
                legal, car, leaves = g.preview(a)
                self.assertTrue(legal)
                before = (len(g.outbound), g.moves, g.index)
                g.step(a)
                self.assertEqual(g.moves, before[1] - 1)
                self.assertEqual(len(g.outbound) - before[0], 1 if leaves else 0)
                self.assertEqual(g.index - before[2], 0 if a[0] == "p" else 1)
                self.assertTrue(all(x <= y for x, y in zip(g.outbound, g.outbound[1:])))
                self.assertTrue(all(len(sd) <= g.cfg["length"] for sd in g.sidings))
                self.assertEqual(len(g.outbound) + sum(len(sd) for sd in g.sidings), g.index)
            self.assertEqual(g.won, len(g.outbound) == g.cfg["cars"])

    def test_render_marks(self):
        g = gm.start(2)
        screen = g.render()
        self.assertIn("OUT    out sends", screen)
        self.assertIn("inbound:", screen)
        g.step(g.demo_action())
        self.assertNotIn("OUT    out sends", g.render())



class Screen(unittest.TestCase):
    """Iterations 7 and 9: tutorial rows on the first move only; dead carriages carry a ! mark."""
    def test_tutorial_only_on_the_first_move(self):
        g = gm.start(2)
        self.assertIn("OUT    out sends", g.render())
        g.step(g.demo_action())
        self.assertNotIn("OUT    out sends", g.render())

    def test_dead_carriages_are_marked(self):
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, cars=3, destinations=3, sidings=1, length=3, moves=10)
        g.train, g.index, g.sidings, g.outbound, g.moves = [3, 1, 2], 0, [[]], [], 10
        g.step("out")
        screen = g.render()
        self.assertIn("inbound:  1! 2!", screen)
        g = gm.start(4, "hard")
        while not g.over:
            last = g.out_last()
            dead = sum(1 for v in g.inbound() if v < last) + sum(1 for s in g.sidings for v in s if v < last)
            self.assertEqual(g.render().count("!"), dead)
            g.step(g.demo_action())


class Saves(unittest.TestCase):
    """Iteration 5: from_state refuses saves that break the rules."""
    def bad(self, **fields):
        st = gm.start(3).to_state()
        st.update(fields)
        with self.assertRaises(ValueError):
            gm.Game.from_state(st)

    def test_round_trip_still_works(self):
        g = gm.start(3)
        for _ in range(5):
            g.step(g.demo_action())
        self.assertEqual(gm.Game.from_state(g.to_state()).status(), g.status())

    def test_bad_saves_are_refused(self):
        g = gm.start(3)
        self.bad(outbound=[1])                             # a carriage that never left the inbound track
        self.bad(index=2, outbound=[g.train[1], g.train[0]] if g.train[1] > g.train[0] else [9, 1])   # order goes down / wrong tags
        self.bad(index=1, sidings=[[g.train[0]], []], moves=g.cfg["moves"])   # a shunt that cost no move
        self.bad(moves=99)
        self.bad(won=True)
        self.bad(over=True)


class Balance(unittest.TestCase):
    """Iteration 3: pinned bands. The yardmaster makes up every train; send-out-when-you-can play stays near zero."""
    NAIVE_BANDS = {"easy": (0, 15), "normal": (0, 10), "hard": (0, 8)}

    @staticmethod
    def naive(g):
        acts = g.actions()
        return "out" if "out" in acts else next((x for x in acts if x[0] == "p"), acts[0])

    def test_yardmaster_makes_up_every_train(self):
        for d in gm.DIFFICULTY:
            for s in range(100):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.demo_action())
                self.assertTrue(g.won, "%s seed %d" % (d, s))

    def test_naive_win_rates(self):
        for d, (low, high) in self.NAIVE_BANDS.items():
            wins = 0
            for s in range(200):
                g = gm.start(s, d)
                while not g.over:
                    g.step(self.naive(g))
                wins += g.won
            self.assertTrue(low <= wins / 2 <= high, "%s naive win rate %.1f%% outside %d-%d" % (d, wins / 2, low, high))


if __name__ == "__main__":
    unittest.main()
