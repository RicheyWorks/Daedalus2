"""Tests for the Prism Satchel shard wallet and Warden Trials seals (prism_satchel.py)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_satchel as ps  # noqa: E402
import prism_satchel_parity as parity  # noqa: E402

GAMES = ("glowmoss", "spiritkite", "glimmerloom", "shadewatch", "shardfall", "prismcairn", "wardens_accord",
         "facetlock", "prismvault", "lumenpath", "shardring")
SEAL = {name: i for i, name in enumerate(ps.SEALS)}


class PayoutTable(unittest.TestCase):
    def test_every_prismheart_game_has_a_payout(self):
        self.assertEqual(sorted(ps.PAYOUTS), sorted(GAMES))
        for game, (hue, div, umbra, heart) in ps.PAYOUTS.items():
            self.assertIn(hue, ps.HUES, game)
            self.assertGreater(div, 0, game)
            self.assertTrue(heart == "perfect" or heart >= umbra > 0, game)

    def test_pars_follow_the_fair_par_table(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engines", "unreal", "core-test",
                            "prism_fair_par_parity.txt")
        rows = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("game="):
                    f = dict(kv.split("=", 1) for kv in line.split())
                    rows[(f["game"], f["difficulty"])] = (int(f["silver"]), int(f["gold"]))
        for game, (_, _, umbra, heart) in ps.PAYOUTS.items():
            silver, gold = rows[(game, "hard")]
            if silver == 0:
                silver, gold = rows[(game, "normal")]
            self.assertEqual(umbra, silver, game)
            self.assertEqual(heart, "perfect" if game == "glowmoss" else gold, game)

    def test_every_hue_is_some_games_home(self):
        self.assertEqual({p[0] for p in ps.PAYOUTS.values()}, set(ps.HUES))


class Record(unittest.TestCase):
    def test_win_pays_base_plus_capped_score_share_plus_new_seals(self):
        s = ps.Satchel()
        self.assertEqual(s.record("shardfall", "easy", 30, True), (1 + 2 + 2, "ember", SEAL["tide"], 2))
        self.assertEqual(s.record("shardfall", "easy", 999, True), (1 + ps.SCORE_CAP, "ember", SEAL["tide"], 0))
        self.assertEqual(s.shards["ember"], 10)
        self.assertEqual(s.runs, 2)

    def test_loss_pays_half_the_score_share_and_earns_ember(self):
        s = ps.Satchel()
        self.assertEqual(s.record("spiritkite", "hard", 40, False), (2 + 1, "gale", SEAL["ember"], 1))
        self.assertEqual(s.record("spiritkite", "hard", 8, False), (0, "gale", SEAL["ember"], 0))

    def test_seal_ladder(self):
        self.assertEqual(ps.seal_for("shardfall", "normal", 0, True), SEAL["verdant"])
        self.assertEqual(ps.seal_for("shardfall", "hard", 33, True), SEAL["gale"])
        self.assertEqual(ps.seal_for("shardfall", "hard", 34, True), SEAL["umbra"])
        self.assertEqual(ps.seal_for("shardfall", "hard", 38, True), SEAL["heartglass"])
        self.assertEqual(ps.seal_for("glowmoss", "hard", 999, True), SEAL["umbra"])
        self.assertEqual(ps.seal_for("glowmoss", "hard", 0, True, True), SEAL["heartglass"])

    def test_perfect_run_bonus_and_heartglass_count(self):
        s = ps.Satchel()
        pay, _, seal, new = s.record("glowmoss", "hard", 24, True, True)
        self.assertEqual((pay, seal, new), (3 + 2 + ps.PERFECT_BONUS + 6, SEAL["heartglass"], 6))
        self.assertEqual(s.heartglass(), 1)

    def test_bad_results_are_refused_and_change_nothing(self):
        s = ps.Satchel()
        for args in (("nogame", "hard", 1, True), ("glowmoss", "brutal", 1, True), ("glowmoss", "hard", -1, True),
                     ("glowmoss", "hard", 1.5, True), ("glowmoss", "hard", True, True), ("glowmoss", "hard", 1, 1),
                     ("glowmoss", "hard", 1, False, True)):
            with self.assertRaises(ValueError, msg=args):
                s.record(*args)
        self.assertEqual(s.to_text(), ps.Satchel().to_text())


class Spend(unittest.TestCase):
    def test_spend_and_refusals(self):
        s = ps.Satchel()
        s.record("shardfall", "hard", 42, True)
        s.spend({"ember": 3})
        self.assertEqual(s.shards["ember"], 3 + 3 + 6 - 3)
        for cost in ({}, {"ember": 0}, {"ember": -1}, {"plaid": 1}, {"ember": True}, {"ember": 99}, {"ember": 1, "tide": 1}, []):
            with self.assertRaises(ValueError, msg=cost):
                s.spend(cost)
        self.assertEqual(s.shards["ember"], 9)


class Save(unittest.TestCase):
    def test_round_trip(self):
        s = ps.Satchel()
        s.record("prismvault", "hard", 100, True)
        s.record("facetlock", "easy", 10, False)
        self.assertEqual(ps.Satchel.from_text(s.to_text()).to_text(), s.to_text())

    def test_tampered_saves_are_rejected(self):
        for text in parity.BAD_SAVES:
            if text.endswith(("glowmoss:4", "glowmoss:6")):
                continue  # well-formed: a seal level is a fact the satchel cannot replay
            with self.assertRaises(ValueError, msg=text):
                ps.Satchel.from_text(text)
        for text in (None, 7, "x" * (ps.SAVE_MAX + 1), "", "PRISMSATCHEL1;0,0,0,0,0;0;glowmoss:\u00b2"):
            with self.assertRaises(ValueError, msg=repr(text)):
                ps.Satchel.from_text(text)


class Parity(unittest.TestCase):
    def test_fixture_is_current(self):
        self.assertEqual(parity.main(["--check"]), 0)

    def test_stale_file_fails_check(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("stale\n")
            self.assertEqual(parity.main(["--check", "--out", path]), 1)


if __name__ == "__main__":
    unittest.main()
