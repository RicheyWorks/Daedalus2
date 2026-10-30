"""Tests for tools/minigames/glimmerloom.py (Glimmerloom Ledger)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import glimmerloom as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_buy_sell_and_limits(self):
        g = gm.start(1, "hard")
        g.prices[0] = 10
        g.step(("buy", 0, 3))
        self.assertEqual((g.purse, g.satchel[0]), (70, 3))
        g.step(("sell", 0, 2))
        self.assertEqual(g.purse, 70 + 2 * (10 - g.cfg["tax"]))
        for bad in (("sell", 0, 5), ("buy", 0, 99), ("buy", 9, 1), ("buy", 0, 0)):
            with self.assertRaises(ValueError):
                g.step(bad)

    def test_rest_applies_rolled_moves_and_clamps(self):
        g = gm.start(2)
        g.prices = [gm.LOW, gm.HIGH, 10, 10]
        g.moves = [-3, 3, 2, -1]
        self.assertEqual(g.step(("rest", 0, 0)), "day 2")
        self.assertEqual(g.prices, [gm.LOW, gm.HIGH, 12, 9])

    def test_rumor_is_mostly_true(self):
        true = total = 0
        for s in range(200):
            g = gm.start(s, "easy")
            hue, word = g.rumor
            total += 1
            true += (g.moves[hue] > 0) == (word == "rise")
        self.assertGreater(true / total, 0.75)

    def test_last_day_sells_all_and_judges(self):
        g = gm.start(3)
        g.day = g.cfg["days"]
        g.prices[1] = 10
        g.satchel = [0, 4, 0, 0]
        g.moves = [0, 0, 0, 0]
        g.purse = g.cfg["target"] - 40
        g.step(("rest", 0, 0))
        self.assertTrue(g.over and g.won)
        self.assertEqual((g.score, g.satchel), (g.cfg["target"], [0, 0, 0, 0]))

    def test_demo_beats_easy_usually(self):
        self.assertGreaterEqual(sum(gm.demo(s, "easy").won for s in range(30)), 20)

    def test_load_rule_check(self):
        g = gm.start(2, "hard")
        g.step(g.demo_action())
        st = g.to_state()
        for breakit in (lambda d: d["prices"].__setitem__(0, gm.HIGH + 1), lambda d: d.update(day=0),
                        lambda d: d["satchel"].__setitem__(0, 99), lambda d: d.update(rumor=[9, "rise"]),
                        lambda d: d.update(over=True), lambda d: d.update(won=True)):
            rejected(self, gm.Game, st, breakit, "rules")
        rejected(self, gm.Game, st, lambda d: d.update(score=d["purse"] + 1), "does not match")


def rejected(test, game_cls, state, breakit, text):
    bad = json.loads(json.dumps(state))
    breakit(bad)
    with test.assertRaisesRegex(ValueError, text):
        game_cls.from_state(bad)


if __name__ == "__main__":
    unittest.main()
