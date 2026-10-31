"""Spirit Boons in prism-shard-dev's games (hephaestus R2-9, accepted by Richey Oct 31, 2026).

A game's BOON = (DIFFICULTY setting, delta per level, spirit). Level 0 is the plain game (fixtures and pars are
unchanged), level 1 is 1-4 summons, level 2 is 5+ summons (doubled). The seed stream is the same at every level.
"""
import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_common as pc  # noqa: E402

GAMES = ("glowmoss", "spiritkite", "facetlock", "lumenpath", "glimmerloom", "shadewatch", "shardfall")
BOONS = {"glowmoss": ("light", 1, "Cinder Wisp"), "spiritkite": ("wind", 2, "Mere Sprite"),
         "facetlock": ("spare", 1, "Thornkin"), "lumenpath": ("moves", 1, "Sky Lark Spirit"),
         "glimmerloom": ("satchel", 2, "Glass Heron"), "shadewatch": ("hearts", 1, "Lantern Newt"),
         "shardfall": ("cracked", -1, "Hollow Moth")}


def boosted():
    for name in GAMES:
        m = importlib.import_module(name)
        if m.Game.BOON is not None:
            yield name, m


class BoonLevels(unittest.TestCase):
    def test_boon_table_matches_hephaestus(self):
        for name, m in boosted():
            self.assertEqual(m.Game.BOON, BOONS[name], name)

    def test_levels_change_one_setting(self):
        for name, m in boosted():
            key, delta, _ = m.Game.BOON
            for diff, base in m.DIFFICULTY.items():
                for level in pc.BOON_LEVELS:
                    g = m.Game(3, diff, level)
                    want = dict(base)
                    want[key] = max(0, base[key] + delta * level)
                    self.assertEqual(g.cfg, want, (name, diff, level))

    def test_level_zero_is_the_plain_game(self):
        for name, m in boosted():
            a, b = m.Game(5, "normal"), m.Game(5, "normal", 0)
            self.assertEqual(a.to_state(), b.to_state(), name)
            self.assertNotIn("boon", a.to_state())

    def test_boosted_saves_round_trip_and_refuse_tampering(self):
        for name, m in boosted():
            g = m.Game(2, "hard", 2)
            g.step(g.demo_action())
            st = g.to_state()
            self.assertEqual(st["boon"], 2)
            self.assertEqual(m.Game.from_state(st).cfg, g.cfg, name)
            for bad in (3, -1, True, "1"):
                st2 = dict(st, boon=bad)
                with self.assertRaises(ValueError, msg=(name, bad)):
                    m.Game.from_state(st2)

    def test_bad_levels_refused(self):
        for name, m in boosted():
            for bad in (3, -1, True, 1.0):
                with self.assertRaises(ValueError, msg=(name, bad)):
                    m.Game(1, "easy", bad)

    def test_games_without_a_boon_refuse_levels(self):
        import prismvault
        with self.assertRaises(ValueError):
            prismvault.Game(1, "easy", 1)


if __name__ == "__main__":
    unittest.main()
