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

    def test_render_marks(self):
        g = self.floor(["20", "32"])
        g.step("0,0")
        screen = g.render()
        self.assertIn("**", screen)
        self.assertIn("##", screen)
        self.assertIn("1/3", screen)


if __name__ == "__main__":
    unittest.main()
