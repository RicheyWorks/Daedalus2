"""Tests for tools/minigames/prismvault.py (Prismvault Weigh)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prismvault as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def test_weigh_results(self):
        g = gm.start(4, "easy")
        h = g.hollow
        other = [i for i in range(8) if i != h]
        self.assertEqual(g.step(("weigh", [h], [other[0]])), "<")
        self.assertEqual(g.step(("weigh", [other[1]], [h])), ">")
        self.assertEqual(g.step(("weigh", [other[2]], [other[3]])), "=")
        self.assertEqual(g.weighings, 0)
        with self.assertRaises(ValueError):
            g.step(("weigh", [0], [1]))
        self.assertEqual(g.step(("name", h)), 100)
        self.assertTrue(g.won)

    def test_bad_weighings_and_wrong_name(self):
        g = gm.start(4)
        for bad in (([0, 1], [2]), ([0], [0]), ([], []), ([99], [0])):
            with self.assertRaises(ValueError):
                g.step(("weigh",) + bad)
        g.step(("name", (g.hollow + 1) % 12))
        self.assertTrue(g.over and not g.won)

    def test_demo_is_optimal(self):
        for d in gm.DIFFICULTY:
            for s in range(40):
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))

    def test_load_replays_weighings(self):
        g = gm.start(2)
        g.step(g.demo_action())
        st = g.to_state()
        self.assertNotIn("hollow", st)
        flip = {"<": ">", ">": "=", "=": "<"}
        for breakit in (lambda d: d["log"][0].__setitem__(2, flip[d["log"][0][2]]), lambda d: d.update(log=[]),
                        lambda d: d.update(candidates=[0]), lambda d: d.update(weighings=99),
                        lambda d: d["log"][0].__setitem__(1, [])):
            rejected(self, gm.Game, st, breakit, "rules")
        rejected(self, gm.Game, st, lambda d: d.update(score=250), "does not match")
        old = dict(st, hollow=(g.hollow + 1) % g.cfg["shards"])
        self.assertEqual(gm.Game.from_state(old).hollow, g.hollow)


def rejected(test, game_cls, state, breakit, text):
    bad = json.loads(json.dumps(state))
    breakit(bad)
    with test.assertRaisesRegex(ValueError, text):
        game_cls.from_state(bad)


if __name__ == "__main__":
    unittest.main()
