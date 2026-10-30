"""Tests for tools/minigames/dyevat.py (Dyevat, G601)."""
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dyevat as gm  # noqa: E402
import prism_testkit as kit  # noqa: E402


class Contract(kit.GameContract, unittest.TestCase):
    MOD = gm


class Rules(unittest.TestCase):
    def rack(self, rows, hues=2, pours=10):
        """Vats bottom to top as digit strings, '-' for empty."""
        g = gm.start(1, "easy")
        g.cfg = dict(g.cfg, hues=hues, empty=sum(r == "-" for r in rows), pours=pours)
        g.vats = [[] if r == "-" else [int(ch) for ch in r] for r in rows]
        g.sealed = [g.full_one_hue(v) for v in range(len(g.vats))]
        g.pours, g.last = pours, [-1, -1]
        return g

    def test_setup_deals_every_hue_capacity_times(self):
        for d, cfg in gm.DIFFICULTY.items():
            g = gm.start(7, d)
            self.assertEqual(len(g.vats), cfg["hues"] + cfg["empty"])
            flat = sorted(x for vat in g.vats for x in vat)
            self.assertEqual(flat, sorted(h for h in range(1, cfg["hues"] + 1) for _ in range(gm.CAPACITY)))
            self.assertTrue(all(not vat for vat in g.vats[cfg["hues"]:]))
            self.assertEqual(g.pours, cfg["pours"])

    def test_same_seed_same_rack(self):
        self.assertEqual(gm.start(3, "hard").vats, gm.start(3, "hard").vats)
        self.assertNotEqual(gm.start(3, "hard").vats, gm.start(4, "hard").vats)

    def test_pour_moves_the_whole_top_run(self):
        g = self.rack(["1122", "-", "1"])
        g.step("0,1")
        self.assertEqual(g.vats[:2], [[1, 1], [2, 2]])

    def test_pour_moves_only_what_fits(self):
        g = self.rack(["1222", "122", "1"])
        g.step("0,1")
        self.assertEqual(g.vats[:2], [[1, 2, 2], [1, 2, 2, 2]])

    def test_mismatch_and_full_and_sealed_are_refused_without_cost(self):
        for rows, act in ((["12", "21", "-"], "0,1"), (["12", "2121", "-"], "0,1"), (["1111", "22", "2"], "0,2")):
            g = self.rack(rows)
            with self.assertRaises(ValueError):
                g.step(act)
            self.assertEqual(g.pours, 10)

    def test_seal_scores_and_win_adds_bonus(self):
        g = self.rack(["2222", "111", "1"], pours=6)
        res = g.step("2,1")
        self.assertTrue(g.won and g.over)
        self.assertEqual(g.score, gm.SEAL_SCORE + gm.POUR_BONUS * 5)
        self.assertIn("every hue sealed", res)

    def test_spent_pours_and_no_pour_left_lose(self):
        g = self.rack(["1212", "2121", "-"], pours=1)
        g.step("0,2")
        self.assertTrue(g.over and not g.won)
        g = self.rack(["1232", "3121", "212"], hues=3)
        self.assertIn("no pour is left", g.step("0,2"))
        self.assertTrue(g.over and not g.won)

    def test_dyer_wins_every_fixture_seed(self):
        for d in gm.DIFFICULTY:
            for s in range(10):
                self.assertTrue(gm.demo(s, d).won, (s, d))

    def test_save_round_trip(self):
        g = gm.start(5)
        g.step(g.demo_action())
        h = gm.Game.from_state(g.to_state())
        self.assertEqual(h.render(), g.render())
        self.assertEqual(h.demo_action(), g.demo_action())

    def test_parity_fixture_is_current(self):
        script = pathlib.Path(__file__).resolve().parent / "dyevat_parity.py"
        self.assertEqual(subprocess.run([sys.executable, str(script), "--check"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
