"""Tests for tools/minigames/sluicegate.py (Sluicegate)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sluicegate as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def field(self, rows, cisterns, mill=None, gates=4, turns=10, flow=2):
        """Rows of '.' channel and '#' rock; the headgate is the channel in row 0 marked 'H'."""
        g = gm.start(1, "easy")
        s = len(rows)
        g.cfg = dict(g.cfg, size=s, cisterns=len(cisterns), gates=gates, turns=turns, flow=flow)
        g.field = [[gm.ROCK if ch == "#" else gm.CHANNEL for ch in row] for row in rows]
        g.head = [0, rows[0].index("H")]
        g.wet = [list(g.head)]
        g.cisterns = [list(c) for c in cisterns]
        g.mill = list(mill) if mill else None
        g.gates, g.gates_left, g.turns, g.filled = [], gates, turns, 0
        return g

    def test_setup(self):
        for d, cfg in gm.DIFFICULTY.items():
            for seed in range(25):
                g = gm.start(seed, d)
                self.assertEqual(g.field[0][cfg["size"] // 2], gm.CHANNEL)
                self.assertEqual(g.wet, [[0, cfg["size"] // 2]])
                self.assertEqual(len(g.cisterns), cfg["cisterns"])
                self.assertEqual(len({tuple(c) for c in g.cisterns}), cfg["cisterns"])
                dist = g._distances(set())
                for c in g.cisterns:
                    self.assertIn(tuple(c), dist, "every cistern is reachable")
                    self.assertLessEqual(dist[tuple(c)], cfg["turns"] - g.cistern_slack())
                self.assertGreaterEqual(len(dist), g.min_reach())
                if g.mill is not None:
                    self.assertNotIn(g.mill, g.cisterns)
                    throats = [(g.mill[0] + dr, g.mill[1] + dc) for dr, dc in gm.NEIGHBOURS
                               if g.inside(g.mill[0] + dr, g.mill[1] + dc) and g.field[g.mill[0] + dr][g.mill[1] + dc] == gm.CHANNEL]
                    self.assertTrue(1 <= len(throats) <= 2, "the mill sits in a dead end (or a two-throat pocket)")
                    for throat in throats:
                        reach = g._distances({throat})
                        self.assertTrue(all(tuple(c) in reach for c in g.cisterns), "gating the throat keeps every cistern reachable")

    def test_flow_wets_nearest_first_in_order(self):
        g = self.field(["..H..", ".....", ".....", ".....", "....."], cisterns=[(4, 4)], flow=2)
        g.step("wait")
        self.assertEqual(g.wet, [[0, 2], [0, 3], [1, 2]], "neighbours east then south of the headgate, FLOW of them")
        g.step("wait")
        self.assertEqual(g.wet[3:], [[0, 1], [0, 4]], "the next push continues from the first wet cells in order")

    def test_gate_blocks_a_branch(self):
        g = self.field(["..H..", ".....", ".....", ".....", "....."], cisterns=[(4, 4)], flow=2)
        g.step("0,3")
        self.assertEqual(g.wet[1:], [[1, 2], [0, 1]], "with the east cell gated the water goes south then west")
        self.assertEqual(g.gates, [[0, 3]])
        self.assertEqual(g.gates_left, 3)

    def test_gate_rules(self):
        g = self.field(["#.H.#", "..#..", ".....", ".....", "....."], cisterns=[(4, 0)], mill=(4, 4))
        for bad in ("0,0", "0,2", "4,0", "4,4", "9,9", "x"):
            with self.assertRaises(ValueError):
                g.step(bad)
        g.step("0,1")
        with self.assertRaises(ValueError):
            g.step("0,1")                                   # already gated
        with self.assertRaises(ValueError):
            g.step("0,3")                                   # wet by now
        g.gates_left = 0
        with self.assertRaises(ValueError):
            g.step("3,2")

    def test_cistern_fills_and_win_scores(self):
        g = self.field(["H##", ".##", ".##"], cisterns=[(2, 0)], gates=3, turns=5, flow=1)
        g.step("wait")
        res = g.step("wait")
        self.assertTrue(g.over and g.won)
        self.assertEqual(g.filled, 1)
        self.assertEqual(g.score, gm.CISTERN_SCORE + 3 * gm.GATE_BONUS + 3 * gm.TURN_BONUS)
        self.assertIn("brims", res)

    def test_mill_floods(self):
        g = self.field(["H.", ".."], cisterns=[(1, 1)], mill=(1, 0), flow=2)
        res = g.step("wait")
        self.assertTrue(g.over and not g.won)
        self.assertIn("mill wheel floods", res)

    def test_headgate_closes_and_channel_runs_dry(self):
        g = self.field(["H.#", "..#", "##."], cisterns=[(2, 2)], turns=2, flow=2)
        g.step("wait")
        res = g.step("wait")
        self.assertTrue(g.over and not g.won)
        self.assertIn("headgate closes", res)
        g = self.field(["H.#", "###", "..."], cisterns=[(2, 0)], turns=9, flow=2)
        g.step("wait")
        res = g.step("wait")
        self.assertIn("runs dry", res)
        self.assertTrue(g.over and not g.won)

    def test_preview_matches_the_move(self):
        for s in range(20):
            g = gm.start(s, "hard")
            while not g.over:
                a = g.demo_action()
                legal, reached, filled, flooded = g.preview(a)
                self.assertTrue(legal)
                state = g.to_state()
                self.assertEqual(g.to_state(), state)
                before = (len(g.wet), g.filled)
                res = g.step(a)
                self.assertEqual((len(g.wet) - before[0], g.filled - before[1]), (len(reached), filled))
                self.assertEqual("floods" in res, flooded)

    def test_gatekeeper_never_floods_the_mill(self):
        for s in range(60):
            g = gm.start(s)
            while not g.over:
                g.step(g.demo_action())
            self.assertFalse(g.mill is not None and g.mill in g.wet)

    def test_properties_hold_under_random_actions(self):
        """Iteration 1: random legal gates and waits on 120 fields never break the bookkeeping."""
        import random
        for s in range(120):
            d = ("easy", "normal", "hard")[s % 3]
            g = gm.start(s, d)
            rng = random.Random(s)
            while not g.over:
                legal = ["wait"] + (["%d,%d" % (r, c) for r in range(g.size()) for c in range(g.size()) if g.gateable(r, c)] if g.gates_left else [])
                a = legal[rng.randrange(len(legal))]
                ok, reached, filled, flooded = g.preview(a)
                self.assertTrue(ok)
                before = (len(g.wet), g.filled, g.gates_left, g.turns)
                res = g.step(a)
                self.assertEqual(g.wet[before[0]:], reached, "the push is the preview, in order")
                self.assertEqual(g.filled - before[1], filled)
                self.assertEqual(before[2] - g.gates_left, 0 if a == "wait" else 1)
                self.assertEqual(before[3] - g.turns, 1)
                self.assertEqual(flooded, "floods" in res)
                self.assertLessEqual(len(reached), g.cfg["flow"])
                for cell in g.wet:
                    self.assertEqual(g.field[cell[0]][cell[1]], gm.CHANNEL)
                    self.assertNotIn(cell, g.gates)
            mill_wet = g.mill is not None and g.mill in g.wet
            self.assertEqual(g.won, g.filled == len(g.cisterns) and not mill_wet)

    def test_render_marks(self):
        g = self.field(["#.H.#", ".....", ".....", ".....", "....."], cisterns=[(4, 0)], mill=(4, 4))
        g.step("1,1")
        screen = g.render()
        self.assertIn("H", screen)
        self.assertIn("~", screen)
        self.assertIn("|", screen)
        self.assertIn("c", screen)
        self.assertIn("M", screen)



class Screen(unittest.TestCase):
    """Iterations 7 and 9: tutorial rows on the first push only; + marks exactly the next push."""
    def test_tutorial_only_on_the_first_push(self):
        g = gm.start(2)
        self.assertIn("FLOW   the headgate", g.render())
        g.step("wait")
        self.assertNotIn("FLOW   the headgate", g.render())

    def test_plus_marks_the_next_push(self):
        g = gm.start(4, "easy")
        while not g.over:
            upcoming = g.preview("wait")[1]
            grid = g.render().split("\n")[1:1 + g.size()]
            marked = [[r, c] for r in range(g.size()) for c in range(g.size()) if grid[r][c] == "+"]
            expected = [cell for cell in upcoming if cell not in g.cisterns and cell != g.mill]
            self.assertEqual(sorted(marked), sorted(expected))
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
        for _ in range(4):
            g.step(g.demo_action())
        self.assertEqual(gm.Game.from_state(g.to_state()).status(), g.status())

    def test_bad_saves_are_refused(self):
        g = gm.start(3)
        self.bad(wet=[[9, 9]])
        self.bad(wet=[list(g.head), list(g.head)])
        self.bad(gates=[list(g.head)], gates_left=g.gates_left - 1)
        self.bad(gates_left=0)
        self.bad(filled=1)
        self.bad(won=True)
        self.bad(turns=0, over=False)


class Balance(unittest.TestCase):
    """Iteration 3: the gatekeeper's win rate stays inside pinned bands, so a rules change that shifts the difficulty is caught."""
    BANDS = {"easy": (80, 98), "normal": (62, 88), "hard": (60, 86)}

    def test_gatekeeper_win_rates(self):
        for d, (low, high) in self.BANDS.items():
            wins = 0
            for s in range(200):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.demo_action())
                wins += g.won
            self.assertTrue(low <= wins / 2 <= high, "%s gatekeeper win rate %.1f%% outside %d-%d" % (d, wins / 2, low, high))


if __name__ == "__main__":
    unittest.main()
