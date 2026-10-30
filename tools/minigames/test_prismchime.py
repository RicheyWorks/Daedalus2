"""Tests for tools/minigames/prismchime.py (Prismchime Ring)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prismchime as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def fixed(self, charge, facing, taps=6):
        g = gm.start(1)
        g.charge, g.facing, g.lit, g.taps = list(charge), list(facing), [False] * len(charge), taps
        return g

    def test_tap_pulses_along_facing_and_resonates(self):
        g = self.fixed([2, 0, 0, 0, 0, 0], [1] * 6)
        self.assertEqual(g.step(0), "tap 0: 0 peal(s)")
        self.assertEqual(g.charge, [3, 1, 1, 0, 0, 0])
        g = self.fixed([2, 0, 0, 0, 0, 0], [-1] * 6)
        g.step(0)
        self.assertEqual(g.charge, [3, 0, 0, 0, 1, 1])

    def test_peal_lights_resets_and_charges_neighbours(self):
        g = self.fixed([3, 0, 0, 0, 0, 0], [1] * 6)
        self.assertEqual(g.step(0), "tap 0: 1 peal(s)")
        self.assertEqual(g.charge, [0, 2, 1, 1, 0, 1])
        self.assertEqual(g.lit, [True, False, False, False, False, False])
        self.assertEqual((g.score, g.peals, g.taps), (5, 1, 5))

    def test_peals_chain_in_fill_order(self):
        g = self.fixed([3, 3, 3, 0, 0, 0], [1] * 6)
        # pulses fill 1 and 2, resonance fills 0: queue [1, 2, 0]; 1 peals (0 -> 5, 2 -> 5), 2 peals (1 -> 1, 3 -> 2),
        # 0 peals from 5 (excess is lost: a peal resets to 0) (5 -> 1, 1 -> 2)
        self.assertEqual(g.step(0), "tap 0: 3 peal(s)")
        self.assertEqual(g.charge, [0, 2, 0, 2, 0, 1])
        self.assertEqual(g.lit, [True, True, True, False, False, False])

    def test_win_scores_tap_bonus_and_loss_ends(self):
        g = self.fixed([3, 3, 3, 3, 3, 3], [1] * 6, taps=4)
        g.step(0)
        self.assertTrue(g.over and g.won)
        self.assertEqual(g.score, 6 * gm.PEAL_SCORE + 3 * gm.TAP_BONUS)
        g = self.fixed([1, 1, 1, 1, 1, 1], [1] * 6, taps=1)
        self.assertTrue(g.step(0).endswith("the ring falls silent"))
        self.assertTrue(g.over and not g.won)

    def test_bad_chime_rejected(self):
        g = gm.start(1)
        with self.assertRaises(ValueError):
            g.step(99)
        with self.assertRaises(ValueError):
            gm.Game.parse("x")

    def test_setup_ranges(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(7, d)
            self.assertEqual(len(g.charge), cfg["chimes"])
            self.assertTrue(all(1 <= c <= 2 for c in g.charge))
            self.assertTrue(all(f in (-1, 1) for f in g.facing))

    def test_greedy_demo_wins_most_easy_rings(self):
        import io
        wins = sum(gm.demo(s, "easy", io.StringIO()).won for s in range(40))
        self.assertGreaterEqual(wins, 30)


if __name__ == "__main__":
    unittest.main()
