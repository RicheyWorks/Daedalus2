"""Tests for tools/minigames/wardens_accord.py (Wardens' Accord)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wardens_accord as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_take_and_summon(self):
        g = gm.start(2)
        hue = g.offer[1]
        rounds = g.rounds
        self.assertEqual(g.step(("take", 1)), 0)
        self.assertEqual((g.pouch[hue], g.rounds), (1, rounds - 1))
        sp = g.spirits[0]
        for h, n in sp["cost"].items():
            g.pouch[h] += n
        self.assertEqual(g.step(("summon", 0)), sp["value"])
        self.assertEqual(g.summoned, [sp["name"]])
        g = gm.start(2)
        self.assertFalse(g.affordable(0))
        with self.assertRaises(ValueError):
            g.step(("summon", 0))
        with self.assertRaises(ValueError):
            g.step(("take", 3))

    def test_win_and_loss(self):
        g = gm.start(3)
        g.score = g.cfg["target"] - 1
        g.spirits[0] = {"name": "x", "cost": {g.hues[0]: 1}, "value": 5}
        g.pouch[g.hues[0]] = 1
        g.step(("summon", 0))
        self.assertTrue(g.won)
        g = gm.start(3)
        g.rounds = 1
        g.spirits = [{"name": "x", "cost": {g.hues[0]: 9}, "value": 5}]
        g.step(("take", 0))
        self.assertTrue(g.over and not g.won)

    def test_spirit_costs_fit_hues(self):
        for d in gm.DIFFICULTY:
            g = gm.start(7, d)
            for s in g.spirits:
                self.assertTrue(set(s["cost"]) <= set(g.hues))
                self.assertTrue(2 <= sum(s["cost"].values()) <= 4)


class SaveChecks(unittest.TestCase):
    """Round 2 finding (prometheus 1): the score must fit the spirits summoned (10-25 each, steps of 5)."""

    def test_tampered_score_and_summons_are_rejected(self):
        g = gm.start(1, "normal")
        while not g.summoned:
            g.step(g.demo_action())
        for edit in ({"score": 9999}, {"score": g.score + 1}, {"summoned": g.summoned + ["Nobody"]}, {"summoned": []}):
            st = g.to_state()
            st.update(edit)
            with self.assertRaises(ValueError, msg=edit):
                gm.Game.from_state(st)
        self.assertEqual(gm.Game.from_state(g.to_state()).score, g.score)


if __name__ == "__main__":
    unittest.main()
