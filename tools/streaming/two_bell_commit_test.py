# SPDX-License-Identifier: MIT
"""Tests for G144 Two-Bell Commit."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import two_bell_commit as b  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "two-bell-commit-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def mv(rs=False, rd=False, crash=None):
    return b.Move("a:0000", "a", "b", rs, rd, crash)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = b.validate(raw())
        self.assertEqual(c.npc_name, "Harbourmaster Ines")
        self.assertEqual((c.protocol, c.moves, c.max_blocked), ("two_bell_log", 600, 400))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["harbour"].update(protocol="three_bell"),
                    lambda d: d["harbour"].update(refuse_permille=1001),
                    lambda d: d["harbour"].update(min_committed=601),
                    lambda d: d["harbour"].update(moves=True),
                    lambda d: d["harbour"].pop("recover_ticks"),
                    lambda d: d.update(islands=[{"id": "only"}]),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("bell")):
            d = raw()
            mut(d)
            with self.assertRaises(b.CommitError):
                b.validate(d)


class MoveTest(unittest.TestCase):
    def state(self):
        return {"a:0000": {"a"}}

    def test_clean_move_commits_everywhere(self):
        for p in b.PROTOCOLS:
            st = self.state()
            self.assertEqual(b.apply_move(st, mv(), p, 5).status, b.COMMITTED)
            self.assertEqual(st["a:0000"], {"b"})

    def test_one_bell_refusal_tears(self):
        st = self.state()
        self.assertEqual(b.apply_move(st, mv(rd=True), "one_bell", 5).status, b.TORN)
        self.assertEqual(st["a:0000"], set())  # deleted at home, never landed: lost
        st = self.state()
        self.assertEqual(b.apply_move(st, mv(rs=True), "one_bell", 5).status, b.TORN)
        self.assertEqual(st["a:0000"], {"a", "b"})  # doubled

    def test_two_bell_refusal_aborts_cleanly(self):
        for p in ("two_bell", "two_bell_log"):
            st = self.state()
            self.assertEqual(b.apply_move(st, mv(rd=True), p, 5).status, b.ABORTED)
            self.assertEqual(st["a:0000"], {"a"})

    def test_crash_without_log_loses_the_save(self):
        st = self.state()
        o = b.apply_move(st, mv(crash=1), "two_bell", 5)
        self.assertEqual((o.status, o.blocked, st["a:0000"]), (b.TORN, 5, set()))

    def test_crash_with_log_recovers(self):
        for heard in (0, 1):
            st = self.state()
            o = b.apply_move(st, mv(crash=heard), "two_bell_log", 5)
            self.assertEqual((o.status, st["a:0000"]), (b.COMMITTED, {"b"}))
            self.assertEqual(o.blocked, (2 - heard) * 5)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = b.validate(raw())

    def test_logged_two_bell_wins(self):
        r = b.simulate(self.c, "two_bell_log")
        self.assertEqual(r.status, b.WON)
        self.assertEqual((r.torn, r.lost_saves, r.duplicated_saves), (0, 0, 0))
        self.assertGreaterEqual(r.committed, self.c.min_committed)
        self.assertLessEqual(r.blocked, self.c.max_blocked)

    def test_traps_tear(self):
        one = b.simulate(self.c, "one_bell")
        self.assertEqual((one.status, one.reason), (b.FAILED, b.FAIL_TORN))
        self.assertGreater(one.lost_saves, 0)
        self.assertGreater(one.duplicated_saves, 0)
        two = b.simulate(self.c, "two_bell")
        self.assertEqual((two.status, two.reason), (b.FAILED, b.FAIL_TORN))
        self.assertGreater(two.lost_saves, 0)
        self.assertEqual(two.duplicated_saves, 0)

    def test_slow_recovery_blows_lock_budget(self):
        d = raw()
        d["harbour"]["recover_ticks"] = 60
        r = b.simulate(b.validate(d), "two_bell_log")
        self.assertEqual((r.status, r.reason), (b.FAILED, b.FAIL_BLOCKED))

    def test_logged_wins_across_seeds_and_accounts(self):
        for seed in range(1, 6):
            d = raw()
            d["seed"] = seed
            r = b.simulate(b.validate(d), "two_bell_log")
            self.assertEqual(r.status, b.WON, seed)
            self.assertEqual(r.committed + r.aborted + r.torn, r.moves)

    def test_deterministic(self):
        self.assertEqual(b.simulate(self.c), b.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = b.islands_from_shoals(json.load(fh))
        c = b.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(b.main([DATA]), 0)
        self.assertEqual(b.main([DATA, "--protocol", "one_bell"]), 1)
        self.assertEqual(b.main([DATA, "--protocol", "two_bell"]), 1)


if __name__ == "__main__":
    unittest.main()
