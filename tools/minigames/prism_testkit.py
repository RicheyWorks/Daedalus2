"""Shared contract tests for the Prismheart campaign games (not discovered on its own)."""
import io
import json
import sys

import catalog_validate as cv


class GameContract:
    """Mix into unittest.TestCase and set MOD (the game module)."""
    MOD = None
    SEEDS = range(12)

    def cls(self):
        return self.MOD.Game

    def test_start_state(self):
        g = self.MOD.start(3)
        self.assertEqual(g.difficulty, "normal")
        self.assertEqual((g.score, g.over, g.won), (0, False, False))
        self.assertTrue(g.render())

    def test_difficulty_table(self):
        self.assertEqual(sorted(self.MOD.DIFFICULTY), ["easy", "hard", "normal"])
        for d in self.MOD.DIFFICULTY:
            self.assertEqual(self.MOD.start(1, d).cfg, self.MOD.DIFFICULTY[d])
        with self.assertRaises(ValueError):
            self.MOD.start(1, "nightmare")

    def test_demo_games_end_deterministically(self):
        for d in self.MOD.DIFFICULTY:
            for s in self.SEEDS:
                a, b = io.StringIO(), io.StringIO()
                ga = self.MOD.demo(s, d, a)
                gb = self.MOD.demo(s, d, b)
                self.assertTrue(ga.over)
                self.assertEqual(a.getvalue(), b.getvalue())
                self.assertEqual(ga.status(), gb.status())
                self.assertGreaterEqual(ga.score, 0)

    def test_seeds_differ(self):
        self.assertNotEqual(self.MOD.start(1).to_state()["rng"], self.MOD.start(2).to_state()["rng"])

    def test_save_load_resumes(self):
        for d in self.MOD.DIFFICULTY:
            g = self.MOD.start(5, d)
            for _ in range(3):
                if not g.over:
                    g.step(g.demo_action())
            h = self.cls().from_state(json.loads(json.dumps(g.to_state())))
            self.assertEqual(h.status(), g.status())
            while not g.over:
                a = g.demo_action()
                self.assertEqual(h.demo_action(), a)
                self.assertEqual(g.step(a), h.step(a))
            self.assertEqual(g.status(), h.status())
        with self.assertRaises(ValueError):
            self.cls().from_state({"v": 9, "id": self.MOD.GAME_ID})

    def test_tampered_saves_are_rejected(self):
        g = self.MOD.start(5)
        if not g.over:
            g.step(g.demo_action())
        good = json.loads(json.dumps(g.to_state()))
        breakages = {
            "negative score": lambda d: d.update(score=-1),
            "text score": lambda d: d.update(score="9999"),
            "rng version": lambda d: d["rng"].__setitem__(0, 2),
            "rng too short": lambda d: d["rng"].__setitem__(1, d["rng"][1][:10]),
            "rng word too big": lambda d: d["rng"][1].__setitem__(0, 2 ** 32),
            "rng gauss": lambda d: d["rng"].__setitem__(2, "x"),
            "missing field": lambda d: d.pop(self.MOD.Game.FIELDS[0]),
        }
        if self.cls()(5).rescore() is not None:
            breakages["inflated score"] = lambda d: d.update(score=d["score"] + 1000)
        for name, breakit in breakages.items():
            bad = json.loads(json.dumps(good))
            breakit(bad)
            with self.assertRaises(ValueError, msg=name):
                self.cls().from_state(bad)

    def test_over_blocks_moves(self):
        g = self.MOD.demo(0, "normal")
        with self.assertRaises(RuntimeError):
            g.step(g.demo_action() if not g.over else None)

    def test_cli_demo_and_play(self):
        self.assertEqual(self.MOD.main(["--demo", "--seed", "2"]), 0)
        out = io.StringIO()
        self.MOD.play(1, "easy", io.StringIO("nonsense\nq\n"), out)
        self.assertIn("? ", out.getvalue())

    def test_original_name(self):
        for t in (self.MOD.TITLE, self.MOD.HOW_TO_PLAY, self.MOD.GAME_ID, self.MOD.__doc__):
            self.assertEqual(cv.trademark_hits(t), [])
        self.assertTrue(self.MOD.HOW_TO_PLAY.startswith("HOW "))
