# SPDX-License-Identifier: MIT
"""G79 Journal Tide tests. Run: python -m unittest tools/streaming/journal_tide_test.py -v"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import journal_tide as jt  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "journal-tide-v1.json")
CORAL = os.path.join(ROOT, "data", "islands", "disk-saver", "coral-wear-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(seed=None, **journal):
    r = raw()
    r["journal"].update(journal)
    if seed is not None:
        r["seed"] = seed
    return jt.validate(r)


def wins(policy, **journal):
    return sum(jt.simulate(cfg(s, **journal), policy).outcome == jt.WON for s in range(1, 41))


class ValidateTest(unittest.TestCase):
    def test_shipped(self):
        c = jt.load(DATA)
        self.assertEqual((c.saves, c.io_budget, c.max_lost, c.surge_permille, c.torn_permille), (200, 50, 30, 15, 50))

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(jt.JournalError):
            jt.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r["journal"].update(io_budget=0))
        self.bad(lambda r: r["journal"].update(io_budget=201))
        self.bad(lambda r: r["journal"].update(surge_permille=1001))
        self.bad(lambda r: r["journal"].pop("max_lost"))
        self.bad(lambda r: r["islands"].append(dict(r["islands"][0])))
        self.bad(lambda r: r["npc"]["lines"].pop("torn"))


class RecordTest(unittest.TestCase):
    def test_record_round_trip_and_crc(self):
        line = jt.record(7, "vault_east", 513)
        self.assertEqual(jt.parse(line), (7, "vault_east", 513))
        self.assertIsNone(jt.parse(line[: len(line) // 2]))      # torn
        self.assertIsNone(jt.parse(line.replace("513", "514")))  # bit rot
        self.assertIsNone(jt.parse("garbage"))

    def test_recover_stops_at_first_bad_record(self):
        lines = [jt.record(1, "a", 1), jt.record(2, "b", 2), jt.record(3, "a", 3)]
        state, good = jt.recover(lines)
        self.assertEqual((state, good), ({"a": 3, "b": 2}, 3))
        torn = lines[:2] + [lines[2][:5]] + [jt.record(4, "b", 9)]
        self.assertEqual(jt.recover(torn), ({"a": 1, "b": 2}, 2))
        gap = [lines[0], lines[2]]                               # seq 1 then 3
        self.assertEqual(jt.recover(gap), ({"a": 1}, 1))


class RulesTest(unittest.TestCase):
    def test_commit_makes_saves_durable(self):
        c = cfg(surge_permille=0, torn_permille=0)
        st = jt.new_state(c)
        jt.step(st, c, False)
        jt.step(st, c, True)
        self.assertEqual((st.commits, st.seq, len(st.buffer)), (1, 2, 0))
        self.assertEqual(jt.recover(st.journal)[0], st.truth)

    def test_surge_loses_buffer_only(self):
        c = cfg(surge_permille=1000, torn_permille=0)
        st = jt.new_state(c)
        jt.step(st, c, False)
        self.assertEqual((st.lost, st.surges, st.seq), (1, 1, 0))
        self.assertIn("surge", st.events)

    def test_torn_commit_recovers_prefix(self):
        c = cfg(surge_permille=0, torn_permille=1000, max_lost=200)
        st = jt.new_state(c)
        for _ in range(5):
            jt.step(st, c, False)
        jt.step(st, c, True)
        self.assertEqual(st.torn, 1)
        self.assertEqual(len(st.journal), st.seq)       # torn tail dropped
        self.assertEqual(jt.recover(st.journal), (st.truth, st.seq))
        self.assertEqual(st.seq + st.lost, 6)

    def test_io_budget_enforced(self):
        c = cfg(surge_permille=0, torn_permille=0, io_budget=1)
        st = jt.new_state(c)
        jt.step(st, c, True)
        with self.assertRaises(jt.JournalError):
            jt.step(st, c, True)

    def test_recovery_always_matches_truth_seeds_1_to_40(self):
        for s in range(1, 41):
            st = jt.simulate(cfg(s, torn_permille=300, max_lost=200))
            self.assertEqual(jt.recover(st.journal), (st.truth, st.seq), s)
            self.assertEqual(st.seq + st.lost, st.saves_done, s)

    def test_over_is_over(self):
        c = jt.load(DATA)
        st = jt.simulate(c)
        with self.assertRaises(jt.JournalError):
            jt.step(st, c, False)


class SeededTest(unittest.TestCase):
    def test_paced_wins_all_and_traps_lose(self):
        self.assertEqual(wins(jt.paced_policy), 40)
        self.assertEqual(wins(jt.every_k(2)), 0)        # ink spent by mid-season
        self.assertLessEqual(wins(jt.end_only_policy), 5)

    def test_deterministic_and_lcg_golden(self):
        self.assertEqual(jt.simulate(cfg(9)).log, jt.simulate(cfg(9)).log)
        r = jt.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_receipt(self):
        c = jt.load(DATA)
        st = jt.simulate(c)
        rc = jt.receipt(st, c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"]), ("q_journal_tide", "journal_tide", "won"))
        self.assertLessEqual(rc["commits"], c.io_budget)
        self.assertEqual(jt.npc_say(st, c)[0], "win")


class TieInTest(unittest.TestCase):
    def test_islands_from_coral(self):
        with open(CORAL, encoding="utf-8") as f:
            coral = json.load(f)
        self.assertEqual(jt.islands_from_coral(coral), raw()["islands"])


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = jt.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--trace")
        self.assertEqual(code, 0)
        self.assertIn("WIN", out)
        code, out, _ = self.run_cli(DATA, "--end-only")
        self.assertIn('"activity": "journal_tide"', out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
