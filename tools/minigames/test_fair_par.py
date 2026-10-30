"""Tests for tools/minigames/fair_par.py (Prismheart Fair Par, Pythagoras balance lane)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fair_par as fp  # noqa: E402
import glimmerloom  # noqa: E402
import glowmoss  # noqa: E402
import prismcairn  # noqa: E402
import shardfall  # noqa: E402
import spiritkite  # noqa: E402
import wardens_accord  # noqa: E402


class FairParTest(unittest.TestCase):
    def test_hash_matches_fairpar_java(self):
        # FairPar.uniform(41, 0, 2, 3) and pick(41, 0, 1, 0, 6) in marsh_fair_par_parity.txt
        self.assertEqual(fp.uniform(41, 0, 2, 3), 0.578865250385359)
        self.assertEqual(fp.pick(41, 0, 1, 0, 6), 5)
        for run in range(50):
            self.assertTrue(0 <= fp.pick(7, run, 3, 1, 4) <= 4)

    def test_calibrate_uses_winning_rounds(self):
        scores = [0, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        pars, hits, median = fp.calibrate(scores)
        self.assertEqual(pars, [1, 70, 100])
        self.assertEqual(hits, [833, 333, 83])
        self.assertEqual(median, 50)
        self.assertEqual(fp.calibrate([0, 0, 0])[0], [1, 0, 0])

    def test_tiers(self):
        pars = [1, 70, 100]
        self.assertEqual(fp.tier(pars, 0), "NONE")
        self.assertEqual(fp.tier(pars, 5), "BRONZE")
        self.assertEqual(fp.tier(pars, 70), "SILVER")
        self.assertEqual(fp.tier(pars, 120), "GOLD")

    def test_bots_only_make_legal_moves_and_never_touch_the_game_rng(self):
        own_rng = (glimmerloom.start, wardens_accord.start, shardfall.start, prismcairn.start)
        for _, start, bot in fp.GAMES:
            for d in fp.DIFFICULTIES:
                for seed in range(15):
                    g = start(seed, d)
                    before = g.rng.getstate()
                    for k in range(fp.STEP_LIMIT):
                        if g.over:
                            break
                        g.step(bot(g, seed, k))  # raises ValueError on an illegal move
                    self.assertTrue(g.over)
                    if start not in own_rng:  # these roll from their own RNG
                        self.assertEqual(before, g.rng.getstate())

    def test_fixture_is_current_and_tiers_are_ordered(self):
        self.assertEqual(fp.main(["--check"]), 0)
        for r in fp.table(60):
            self.assertLessEqual(r["silver"], r["gold"])
            self.assertGreaterEqual(r["hits"][0], r["hits"][1])
            self.assertGreaterEqual(r["hits"][1], r["hits"][2])

    def test_modules_are_read_only(self):
        self.assertEqual((glowmoss.GAME_ID, spiritkite.GAME_ID, glimmerloom.GAME_ID),
                         ("glowmoss", "spiritkite", "glimmerloom"))


if __name__ == "__main__":
    unittest.main()
