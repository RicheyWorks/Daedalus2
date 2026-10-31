"""Tests for tools/minigames/emberkiln.py (Emberkiln)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import emberkiln as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def floor(self, rows, coals=10):
        """Rows of digits: 0 stone, 2-4 targets. Heat starts at 0."""
        g = gm.start(1, "easy")
        s = len(rows)
        g.cfg = dict(g.cfg, size=s, stone=sum(ch == "0" for row in rows for ch in row), coals=coals)
        g.target = [[int(ch) for ch in row] for row in rows]
        g.heat = [[0] * s for _ in range(s)]
        g.coals, g.glazed, g.cracked = coals, 0, 0
        return g

    def test_setup(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(9, d)
            self.assertEqual(sum(t == gm.STONE for row in g.target for t in row), cfg["stone"])
            self.assertTrue(all(t in gm.TARGETS or t == gm.STONE for row in g.target for t in row))
            self.assertEqual(g.clay(), cfg["size"] ** 2 - cfg["stone"])
            self.assertEqual(g.coals, cfg["coals"])

    def test_coal_heats_the_tile_by_two_and_neighbours_by_one(self):
        g = self.floor(["333", "343", "333"])
        g.step("1,1")
        self.assertEqual(g.heat[1][1], 2)
        self.assertEqual([g.heat[0][1], g.heat[1][0], g.heat[1][2], g.heat[2][1]], [1, 1, 1, 1])
        self.assertEqual(g.heat[0][0], 0, "diagonals take no heat")

    def test_exact_heat_glazes_and_overshoot_cracks(self):
        g = self.floor(["222", "232", "222"])
        res = g.step("1,1")
        self.assertEqual((g.glazed, g.cracked), (0, 0))
        self.assertIn("0 glazed, 0 cracked", res)
        g.step("1,1")
        self.assertEqual(g.target[1][1], gm.CRACKED, "4 heat on a target of 3 cracks")
        self.assertEqual([g.target[0][1], g.target[1][0], g.target[1][2], g.target[2][1]], [gm.GLAZED] * 4)
        self.assertEqual((g.glazed, g.cracked, g.score), (4, 1, 4 * gm.GLAZE_SCORE + gm.CRACK_SCORE))

    def test_stone_and_finished_tiles_take_no_heat_but_spread(self):
        g = self.floor(["020", "232", "020"])
        g.step("0,0")                       # stone corner: only (0,1) and (1,0) warm
        self.assertEqual(g.heat[0][0], 0)
        self.assertEqual((g.heat[0][1], g.heat[1][0]), (1, 1))
        g.step("1,1")                       # centre 3: +2 → 2; (0,1) 1+1 = 2 glazes; (1,0) glazes
        self.assertEqual(g.target[0][1], gm.GLAZED)
        g.step("0,1")                       # on a glazed tile: it stays glazed, centre reaches 3 and glazes
        self.assertEqual(g.target[0][1], gm.GLAZED)
        self.assertEqual(g.target[1][1], gm.GLAZED)

    def test_illegal_cells(self):
        g = self.floor(["22", "22"])
        for bad in ("5,0", "a", "1", "-1,0"):
            with self.assertRaises(ValueError):
                g.step(bad)
        self.assertEqual(g.coals, 10, "refused coals cost nothing")

    def test_win_needs_every_tile_glazed_and_no_crack(self):
        g = self.floor(["20", "00"], coals=3)
        res = g.step("0,0")
        self.assertTrue(g.over and g.won)
        self.assertEqual(g.score, gm.GLAZE_SCORE + 2 * gm.COAL_BONUS)
        self.assertIn("shines", res)
        g = self.floor(["30", "02"], coals=5)
        g.step("1,1")                      # glazes (1,1)
        g.step("0,0")                      # heat 2 on a target of 3
        g.step("0,0")                      # 4 > 3 cracks it: the floor is finished but spoiled
        self.assertTrue(g.over and not g.won)
        self.assertIn("spoiled", g.render())

    def test_spent_coals_lose(self):
        g = self.floor(["44", "44"], coals=1)
        g.step("0,0")
        self.assertTrue(g.over and not g.won)

    def test_preview_matches_the_move(self):
        for s in range(20):
            g = gm.start(s, "hard")
            while not g.over:
                a = g.demo_action()
                r, c = g.parse_cell(a)
                glazes, cracks, raised = g.preview(r, c)
                state = g.to_state()
                self.assertEqual(g.to_state(), state)
                before = (g.glazed, g.cracked)
                g.step(a)
                self.assertEqual((g.glazed - before[0], g.cracked - before[1]), (glazes, cracks))

    def test_stoker_never_cracks_when_a_safe_coal_exists(self):
        for s in range(60):
            g = gm.start(s)
            while not g.over:
                g.step(g.demo_action())
            self.assertEqual(g.cracked, 0)

    def test_properties_hold_under_random_coals(self):
        """Iteration 1: random legal coals on 120 floors never break the bookkeeping or the heat bounds."""
        import random
        for s in range(120):
            d = ("easy", "normal", "hard")[s % 3]
            g = gm.start(s, d)
            rng = random.Random(s)
            clay = g.cfg["size"] ** 2 - g.cfg["stone"]
            while not g.over:
                r, c = rng.randrange(g.size()), rng.randrange(g.size())
                glazes, cracks, _ = g.preview(r, c)
                before = (g.glazed, g.cracked, g.coals, g.score)
                g.step("%d,%d" % (r, c))
                self.assertEqual((g.glazed - before[0], g.cracked - before[1], before[2] - g.coals), (glazes, cracks, 1))
                self.assertEqual(g.glazed + g.cracked + g.clay(), clay)
                if not g.won:
                    self.assertEqual(g.score, before[3] + gm.GLAZE_SCORE * glazes + gm.CRACK_SCORE * cracks)
                for rr in range(g.size()):
                    for cc in range(g.size()):
                        t, h = g.target[rr][cc], g.heat[rr][cc]
                        if t == gm.STONE:
                            self.assertEqual(h, 0)
                        elif t > 0:
                            self.assertLess(h, t)
                        else:
                            self.assertIn(t, (gm.GLAZED, gm.CRACKED))
            self.assertTrue(g.clay() == 0 or g.coals == 0)
            self.assertEqual(g.won, g.clay() == 0 and g.cracked == 0)

    def test_render_marks(self):
        g = self.floor(["20", "32"])
        g.step("0,0")
        screen = g.render()
        self.assertIn("**", screen)
        self.assertIn("##", screen)
        self.assertIn("1/3", screen)



class Screen(unittest.TestCase):
    """Iterations 7 and 9: tutorial rows on the first coal only; the safe-cell count tracks the preview."""
    def test_tutorial_only_on_the_first_coal(self):
        g = gm.start(2)
        self.assertIn("COAL   r,c", g.render())
        g.step(g.demo_action())
        self.assertNotIn("COAL   r,c", g.render())

    def test_safe_cells_count_matches_preview(self):
        g = gm.start(4, "easy")
        while not g.over:
            expect = sum(1 for r in range(g.size()) for c in range(g.size()) if g.preview(r, c)[1] == 0)
            self.assertIn("safe cells %d" % expect, g.render())
            g.step(g.demo_action())
        self.assertNotIn("safe cells", g.render())


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
        heat = [row[:] for row in g.heat]
        r, c = next((r, c) for r in range(g.size()) for c in range(g.size()) if g.target[r][c] > 0)
        heat[r][c] = g.target[r][c]
        self.bad(heat=heat)                                 # a raw tile sitting on its target
        self.bad(target=[row[:-1] for row in g.target])     # wrong shape
        self.bad(coals=99)
        self.bad(glazed=1)
        self.bad(won=True)
        self.bad(over=True)


class Balance(unittest.TestCase):
    """Iteration 3: the stoker's win rate stays inside pinned bands, so a rules change that shifts the difficulty is caught."""
    BANDS = {"easy": (65, 90), "normal": (70, 95), "hard": (70, 95)}

    def test_stoker_win_rates(self):
        for d, (low, high) in self.BANDS.items():
            wins = 0
            for s in range(200):
                g = gm.start(s, d)
                while not g.over:
                    g.step(g.demo_action())
                wins += g.won
            self.assertTrue(low <= wins / 2 <= high, "%s stoker win rate %.1f%% outside %d-%d" % (d, wins / 2, low, high))


if __name__ == "__main__":
    unittest.main()
