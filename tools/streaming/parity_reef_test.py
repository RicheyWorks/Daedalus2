# SPDX-License-Identifier: MIT
"""G67 Parity Reef tests. Run: python -m unittest tools/streaming/parity_reef_test.py -v"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parity_reef as pr  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "parity-reef-v1.json")
DEFRAG = os.path.join(ROOT, "data", "islands", "disk-saver", "defrag-tide-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(seed=None, **reef):
    r = raw()
    r["reef"].update(reef)
    if seed is not None:
        r["seed"] = seed
    return pr.validate(r)


def idle(state, config):
    return []


def storm_on(state, config, stone):
    for j in range(config.stripes):
        state.blocks[stone][j] = 0
        state.ok[stone][j] = False


class ValidateTest(unittest.TestCase):
    def test_shipped(self):
        c = pr.load(DATA)
        self.assertEqual((c.stones, c.stripes, c.rebuild_per_tick, c.calm_ticks), (5, 8, 2, 4))

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(pr.ReefError):
            pr.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r["reef"].update(stones=2))
        self.bad(lambda r: r["reef"].update(stripes=0))
        self.bad(lambda r: r["reef"].update(storm_permille=1001))
        self.bad(lambda r: r["reef"].update(calm_ticks=False))
        self.bad(lambda r: r["reef"].pop("season_ticks"))
        self.bad(lambda r: r["npc"]["lines"].pop("storm"))
        self.bad(lambda r: r["npc"].update(name=""))


class ParityTest(unittest.TestCase):
    def test_every_stripe_xors_to_zero_and_parity_rotates(self):
        c = pr.load(DATA)
        st = pr.new_state(c)
        for j in range(c.stripes):
            self.assertEqual(pr.stripe_xor(st, j), 0)
        self.assertEqual([pr.parity_slot(j, 5) for j in range(6)], [4, 3, 2, 1, 0, 4])

    def test_reconstruct_any_single_block(self):
        c = pr.load(DATA)
        st = pr.new_state(c)
        for s in range(c.stones):
            for j in range(c.stripes):
                self.assertEqual(pr.reconstruct(st, j, s), st.truth[s][j])

    def test_second_missing_block_cannot_reconstruct(self):
        c = pr.load(DATA)
        st = pr.new_state(c)
        st.ok[1][0] = False
        with self.assertRaises(pr.ReefError):
            pr.reconstruct(st, 0, 2)


class RulesTest(unittest.TestCase):
    def test_rebuild_restores_and_verifies(self):
        c = cfg(storm_permille=0)
        st = pr.new_state(c)
        storm_on(st, c, 2)
        while st.missing():
            pr.tick(st, c, pr.keeper_policy(st, c))
        self.assertEqual(st.blocks, st.truth)
        self.assertEqual(st.rebuilt, c.stripes)
        self.assertIn("healthy", st.events)

    def test_tick_errors(self):
        c = cfg(storm_permille=0)
        st = pr.new_state(c)
        with self.assertRaises(pr.ReefError):
            pr.tick(st, c, [(0, 0)])  # not missing
        storm_on(st, c, 0)
        with self.assertRaises(pr.ReefError):
            pr.tick(st, c, [(0, 0), (0, 1), (0, 2)])  # over budget
        with self.assertRaises(pr.ReefError):
            pr.tick(st, c, [(9, 0)])

    def test_double_loss_fails(self):
        c = cfg(storm_permille=0)
        st = pr.new_state(c)
        storm_on(st, c, 0)
        st.ok[1][3] = False
        pr.tick(st, c, [])
        self.assertEqual((st.outcome, st.fail_reason), (pr.FAILED, pr.FAIL_LOST))
        self.assertEqual(pr.npc_say(st, c)[0], "fail")

    def test_calm_after_storm(self):
        c = cfg(storm_permille=1000, calm_ticks=3)
        st = pr.new_state(c)
        pr.tick(st, c, [])
        self.assertIn("storm", st.events)
        for _ in range(3):
            pr.tick(st, c, pr.keeper_policy(st, c))
            self.assertNotIn("storm", st.events)

    def test_no_storms_wins(self):
        st = pr.simulate(cfg(storm_permille=0), idle)
        self.assertEqual(st.outcome, pr.WON)
        self.assertEqual(st.storms, 0)


class SeededTest(unittest.TestCase):
    def test_keeper_wins_idle_loses_seeds_1_to_40(self):
        for seed in range(1, 41):
            c = cfg(seed)
            good = pr.simulate(c)
            self.assertEqual(good.outcome, pr.WON, seed)
            self.assertGreaterEqual(good.storms, 2, seed)
            self.assertEqual(pr.simulate(c, idle).fail_reason, pr.FAIL_LOST, seed)

    def test_slow_rebuild_loses_some_seed(self):
        # 8 blocks at 1 per tick outlast the 4-tick calm: a storm can hit mid-rebuild.
        lost = [s for s in range(1, 41) if pr.simulate(cfg(s, rebuild_per_tick=1)).outcome == pr.FAILED]
        self.assertTrue(lost)

    def test_deterministic_and_lcg_golden(self):
        self.assertEqual(pr.simulate(cfg(3)).log, pr.simulate(cfg(3)).log)
        r = pr.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_receipt(self):
        c = pr.load(DATA)
        st = pr.simulate(c)
        rc = pr.receipt(st, c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"]), ("q_parity_reef", "parity_reef", "won"))
        self.assertEqual(rc["score"], st.storms * 100)


class TieInTest(unittest.TestCase):
    def test_stripes_from_defrag_g63(self):
        with open(DEFRAG, encoding="utf-8") as f:
            defrag = json.load(f)
        c = pr.load(DATA)
        self.assertEqual(pr.stripes_from_defrag(defrag, c.stones), c.stripes)
        with self.assertRaises(pr.ReefError):
            pr.stripes_from_defrag(defrag, 2)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pr.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--seed", "1", "--trace")
        self.assertEqual(code, 0)
        self.assertIn("WIN", out)
        code, out, _ = self.run_cli(DATA, "--idle", "--trace")
        self.assertEqual(code, 1)
        self.assertIn("FAIL data_lost", out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
