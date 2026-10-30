"""Tests for tools/minigames/glowmoss.py (Glowmoss Delve)."""
import json
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import glowmoss as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm
    SEEDS = range(6)


def tiny_cfg(light=6, refill=3):
    return {"cols": 2, "rows": 3, "light": light, "refill": refill, "moss_pct": 0, "unstable_pct": 0, "target_pct": 100}


def flat():
    return [[False, False], [False, False], [False, False]]


class Rules(unittest.TestCase):
    def test_climb_cost_and_reach(self):
        self.assertEqual([gm.climb_cost(r) for r in (-1, 0, 1, 2, 3, 4)], [0, 1, 1, 2, 2, 3])
        self.assertEqual(list(gm.dig_cols(0, 4)), [0, 1])
        self.assertEqual(list(gm.dig_cols(3, 4)), [2, 3])

    def test_after_dig_refill_is_capped(self):
        cfg = tiny_cfg()
        self.assertEqual(gm.after_dig(6, cfg, 2, False), 3)
        self.assertEqual(gm.after_dig(6, cfg, 0, True), 6)
        self.assertEqual(gm.after_dig(1, cfg, 1, True), 2)

    def test_best_delve_exact(self):
        gems = [[1, 9], [5, 1], [1, 1]]
        dark = [[0, 2], [0, 0], [0, 0]]
        # Start above column 1 with 6 light: 9 costs 3 (light 3), then 5 costs 1 (light 2 >= climb 1), the bottom needs 2 more.
        self.assertEqual(gm.best_delve(tiny_cfg(), (gems, dark, flat(), flat())), (14, [1, 0]))
        moss = flat()
        moss[0][1] = True
        self.assertEqual(gm.best_delve(tiny_cfg(), (gems, dark, moss, flat())), (15, [1, 0, 0]))
        self.assertEqual(gm.best_delve(tiny_cfg(light=1), (gems, dark, flat(), flat())), (0, []))

    def test_unstable_ledge_falls(self):
        gems = [[1, 9], [5, 1], [1, 1]]
        dark = [[0, 2], [0, 0], [0, 0]]
        unstable = flat()
        unstable[0][1] = True
        shaft = (gems, dark, flat(), unstable)
        self.assertEqual(gm.land(tiny_cfg(), shaft, 0, 1, 6), (1, 3, 10, False, True))
        unstable[2][0] = True
        self.assertFalse(gm.land(tiny_cfg(), shaft, 2, 0, 6)[4])
        # 9 + 1 by the fall (light 3 on row 1), then either bottom ledge (lowest column on ties): 3 - 1 = 2 covers climb 2.
        self.assertEqual(gm.best_delve(tiny_cfg(), shaft), (11, [1, 0]))

    def test_perfect_delve_bonus(self):
        g = gm.demo(5, "easy")
        self.assertTrue(g.won and g.perfect)
        self.assertEqual(g.score, g.crystals + g.light + gm.PERFECT_BONUS)

    def test_demo_follows_the_best_plan_and_wins(self):
        for d in gm.DIFFICULTY:
            for s in range(15):
                g = gm.demo(s, d)
                self.assertTrue(g.won, (d, s))
                self.assertEqual(g.path, g.plan)
                self.assertGreaterEqual(g.crystals, g.target)

    def test_dig_rules_and_guttering(self):
        g = gm.start(3)
        with self.assertRaises(ValueError):
            g.step(("dig", g.col + 2))
        c = g.col
        light = g.light
        res = g.step(("dig", c))
        self.assertEqual((g.row, g.col, g.crystals), (0, c, g.gems[0][c]))
        self.assertTrue(res.startswith("+%d" % g.gems[0][c]))
        self.assertLessEqual(g.light, light)
        g = gm.start(3)
        g.light = 1 + g.dark[0][g.col]
        g.moss[0][g.col] = False
        g.unstable[0][g.col] = False
        self.assertEqual(g.step(("dig", g.col)), "the lamp gutters out")
        self.assertTrue(g.over and not g.won)

    def test_climb_short_of_target_loses(self):
        g = gm.start(4)
        self.assertEqual(g.step(("climb", 0)), "climbed out with 0")
        self.assertTrue(g.over and not g.won)
        self.assertEqual(g.score, 0)


    def test_hint_follows_the_best_delve(self):
        for d in gm.DIFFICULTY:
            for s in range(10):
                g = gm.start(s, d)
                while not g.over:
                    self.assertEqual(g.hint(), g.demo_action(), (d, s, g.path))
                    g.step(g.demo_action())
        g = gm.start(1)
        g.row = g.cfg["rows"] - 1
        self.assertEqual(g.hint(), ("climb", 0))

    def test_seed_codes_and_daily_seed(self):
        self.assertEqual(gm.seed_code(1337, "normal"), "GLOW-N-1337")
        self.assertEqual(gm.parse_seed_code("  glow-h-42 "), (42, "hard"))
        for d in gm.DIFFICULTY:
            self.assertEqual(gm.parse_seed_code(gm.seed_code(7, d)), (7, d))
        for bad in ("x", "GLOW-Q-1", "GLOW-N-", "GLOW-N-1x", "GLOWN-1"):
            with self.assertRaises(ValueError):
                gm.parse_seed_code(bad)
        self.assertEqual(gm.daily_seed(2026, 10, 30), 20261030)

    def test_clear_errors(self):
        g = gm.start(1)
        cases = {("dig", 9): "you can dig columns 1-3", ("fly", 1): "unknown action", ("dig", "1"): "not '1'"}
        for action, text in cases.items():
            with self.assertRaises(ValueError) as e:
                g.step(action)
            self.assertIn(text, str(e.exception))
        g.row = g.cfg["rows"] - 1
        with self.assertRaisesRegex(ValueError, "shaft floor"):
            g.step(("dig", g.col))
        self.assertEqual(gm.Game.parse(" Climb "), ("climb", 0))
        self.assertEqual(gm.Game.parse("DIG 2"), ("dig", 2))
        with self.assertRaisesRegex(ValueError, "column number"):
            gm.Game.parse("dig x")
        with self.assertRaisesRegex(ValueError, "use dig"):
            gm.Game.parse("dig")


    def test_save_carries_rules_version_and_is_validated(self):
        g = gm.start(2, "hard")
        g.step(g.demo_action())
        st = g.to_state()
        self.assertEqual(st["rules"], gm.RULES_VERSION)
        self.assertEqual(gm.Game.from_state(json.loads(json.dumps(st))).status(), g.status())
        breakages = {
            "rules version": lambda d: d.update(rules=1),
            "unknown difficulty": lambda d: d.update(difficulty="mythic"),
            "grid 'gems'": lambda d: d["gems"].pop(),
            "grid 'dark'": lambda d: d["dark"][0].__setitem__(0, 7),
            "grid 'unstable'": lambda d: d.update(unstable="none"),
            "outside the shaft": lambda d: d.update(col=99),
            "lamp": lambda d: d.update(light=999),
            "path": lambda d: d.update(path=[0, 0, 0, 0, 0]),
        }
        for text, breakit in breakages.items():
            bad = json.loads(json.dumps(st))
            breakit(bad)
            with self.assertRaises(ValueError) as e:
                gm.Game.from_state(bad)
            self.assertIn(text.split()[-1].strip("'"), str(e.exception), text)

    def test_render_shows_lamp_legend_and_reach(self):
        g = gm.start(3)
        text = g.render()
        self.assertIn("GLOW-N-3", text)
        self.assertIn("lamp [############]", text)
        self.assertIn("legend:", text)
        self.assertEqual(text.splitlines()[4].count("v"), len(gm.dig_cols(g.col, g.cfg["cols"])))
        g = gm.demo(5, "easy")
        self.assertIn("WON (perfect delve)", g.render())
        g = gm.start(4)
        g.step(("climb", 0))
        self.assertIn("short of the target", g.render())

    def test_tutorial_help_and_hint_commands(self):
        self.assertIn("how to play", gm.TUTORIAL)
        with self.assertRaisesRegex(ValueError, "how to play"):
            gm.Game.parse("help")
        g = gm.start(1)
        before = g.status()
        self.assertEqual(g.step(gm.Game.parse("hint")), "hint: dig %d" % g.plan[0])
        self.assertEqual(g.status(), before)
        self.assertEqual(gm.main(["--tutorial"]), 0)



class Properties(unittest.TestCase):
    """Property sweeps over many seeds: the invariants every shaft must keep."""
    SEEDS = range(60)

    def test_target_always_reachable_and_demo_perfect(self):
        for d in gm.DIFFICULTY:
            for s in self.SEEDS:
                g = gm.start(s, d)
                self.assertTrue(1 <= g.target <= g.best, (d, s))
                g = gm.demo(s, d)
                self.assertTrue(g.won and g.perfect, (d, s))
                self.assertEqual(g.crystals, g.best)

    def test_same_seed_same_shaft(self):
        for d in gm.DIFFICULTY:
            for s in self.SEEDS:
                self.assertEqual(gm.start(s, d).status(), gm.start(s, d).status())

    def test_save_load_round_trip_at_every_step(self):
        for d in gm.DIFFICULTY:
            for s in range(10):
                g = gm.start(s, d)
                while True:
                    h = gm.Game.from_state(json.loads(json.dumps(g.to_state())))
                    self.assertEqual(h.status(), g.status())
                    self.assertEqual(h.render(), g.render())
                    if g.over:
                        break
                    a = g.demo_action()
                    self.assertEqual(g.step(a), h.step(a))

    def test_any_legal_dig_keeps_state_consistent(self):
        rng = random.Random("glowmoss-props")
        for d in gm.DIFFICULTY:
            for s in self.SEEDS:
                g = gm.start(s, d)
                while not g.over:
                    if g.row + 1 >= g.cfg["rows"] or rng.random() < 0.1:
                        g.step(("climb", 0))
                        break
                    g.step(("dig", rng.choice(list(gm.dig_cols(g.col, g.cfg["cols"])))))
                    self.assertLessEqual(g.light, g.cfg["light"])
                    self.assertLessEqual(len(g.path), g.row + 1)
                    self.assertEqual(g.over, g.light < gm.climb_cost(g.row))
                self.assertGreaterEqual(g.score, 0)

    def test_greedy_player_beats_random(self):
        import glowmoss_sim as sim
        for d in gm.DIFFICULTY:
            self.assertGreater(sim.win_rate("greedy", d, 60), sim.win_rate("random", d, 60), d)


if __name__ == "__main__":
    unittest.main()
