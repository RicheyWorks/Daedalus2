# SPDX-License-Identifier: MIT
"""G63 Defrag Tide tests. Run: python -m unittest tools/streaming/defrag_tide_test.py -v"""
import copy
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import defrag_tide as dt  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "defrag-tide-v1.json")
SPRING = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(**over):
    r = raw()
    r.update(over)
    return dt.validate(r)


def idle(state, config):
    return []


def tiny(**disk):
    r = raw()
    r["disk"] = dict({"blocks": 10, "block_kib": 1, "moves_per_tide": 2, "tides": 3, "seek_target": 0}, **disk)
    r["files"] = [{"id": "a", "blocks": 3, "priority": 2}]
    return dt.validate(r)


class ValidateTest(unittest.TestCase):
    def test_shipped_valid(self):
        c = dt.load(DATA)
        self.assertEqual((c.blocks, c.moves_per_tide, c.tides, c.seek_target), (96, 4, 12, 4))
        self.assertEqual(c.npc_name, "Tidewright Seek")

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(dt.DefragError):
            dt.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r["disk"].pop("tides"))
        self.bad(lambda r: r["disk"].update(blocks=True))
        self.bad(lambda r: r["disk"].update(moves_per_tide=0))
        self.bad(lambda r: r["disk"].update(blocks=40))  # caches + erosion would fill it
        self.bad(lambda r: r["files"].append(copy.deepcopy(r["files"][0])))
        self.bad(lambda r: r["files"][0].update(id="no spaces"))
        self.bad(lambda r: r["files"][0].update(priority=0))
        self.bad(lambda r: r.update(files=[]))
        self.bad(lambda r: r["npc"]["lines"].pop("win"))
        self.bad(lambda r: r["npc"]["lines"].update(win="x" * 201))


class RulesTest(unittest.TestCase):
    def test_scatter_places_every_block_once(self):
        c = dt.load(DATA)
        st = dt.new_state(c)
        taken = [x for x in st.disk if x is not dt.FREE]
        self.assertEqual(len(taken), sum(f.blocks for f in c.files))
        for f in c.files:
            for k, slot in enumerate(st.where[f.id]):
                self.assertEqual(st.disk[slot], (f.id, k))

    def test_runs_and_seeks(self):
        c = tiny()
        st = dt.new_state(c)
        for k, dest in enumerate((7, 8, 9)):
            if st.disk[dest] is not dt.FREE and st.disk[dest] != ("a", k):
                other = st.disk[dest]
                dt.move(st, other[0], other[1], next(i for i, x in enumerate(st.disk) if x is dt.FREE and i < 7))
            if st.disk[dest] != ("a", k):
                dt.move(st, "a", k, dest)
        self.assertEqual(dt.runs(st, "a"), 1)
        self.assertEqual(dt.seeks(st, c), 0)
        dt.move(st, "a", 1, next(i for i, x in enumerate(st.disk) if x is dt.FREE))
        self.assertEqual(dt.runs(st, "a"), 3)
        self.assertEqual(dt.seeks(st, c), 4)  # priority 2 * (3 - 1)

    def test_move_errors(self):
        c = dt.load(DATA)
        st = dt.new_state(c)
        busy = st.where["vault_east"][0]
        with self.assertRaises(dt.DefragError):
            dt.move(st, "cache_north", 0, busy)
        with self.assertRaises(dt.DefragError):
            dt.move(st, "nope", 0, 0)
        with self.assertRaises(dt.DefragError):
            dt.move(st, "cache_north", 99, 0)
        with self.assertRaises(dt.DefragError):
            dt.tick(st, c, [("a", 0, 0)] * (c.moves_per_tide + 1))

    def test_erosion_only_eats_free_blocks(self):
        c = dt.load(DATA)
        st = dt.new_state(c)
        cached = sum(1 for x in st.disk if isinstance(x, tuple))
        for _ in range(5):
            dt.tick(st, c, [])
        self.assertEqual(sum(1 for x in st.disk if x == dt.BAD), 5)
        self.assertEqual(sum(1 for x in st.disk if isinstance(x, tuple)), cached)
        with self.assertRaises(dt.DefragError):
            dt.move(st, "cache_north", 0, st.disk.index(dt.BAD))

    def test_idle_fails_seeds_1_to_20(self):
        for seed in range(1, 21):
            st = dt.simulate(cfg(seed=seed), idle)
            self.assertEqual((st.outcome, st.fail_reason), (dt.FAILED, dt.FAIL_TIDES), seed)
            self.assertEqual(dt.npc_say(st, cfg(seed=seed))[0], "fail")

    def test_planner_does_not_touch_live_state(self):
        c = dt.load(DATA)
        st = dt.new_state(c)
        before = list(st.disk)
        plan = dt.keeper_policy(st, c)
        self.assertEqual(st.disk, before)
        self.assertLessEqual(len(plan), c.moves_per_tide)
        dt.tick(st, c, plan)  # plan replays legally

    def test_over_is_over(self):
        c = dt.load(DATA)
        st = dt.simulate(c)
        with self.assertRaises(dt.DefragError):
            dt.tick(st, c, [])


class SeededTest(unittest.TestCase):
    def test_keeper_wins_seeds_1_to_40(self):
        for seed in range(1, 41):
            c = cfg(seed=seed)
            st = dt.simulate(c)
            self.assertEqual(st.outcome, dt.WON, seed)
            self.assertLessEqual(dt.seeks(st, c), c.seek_target)
            self.assertLessEqual(st.moves_used, st.tide * c.moves_per_tide)

    def test_deterministic(self):
        self.assertEqual(dt.simulate(cfg(seed=5)).log, dt.simulate(cfg(seed=5)).log)
        self.assertNotEqual(dt.new_state(cfg(seed=5)).where, dt.new_state(cfg(seed=6)).where)

    def test_lcg_golden_shared_with_g39_g59(self):
        r = dt.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_receipt(self):
        c = dt.load(DATA)
        st = dt.simulate(c)
        rc = dt.receipt(st, c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"]), ("q_defrag_tide", "defrag_tide", "won"))
        self.assertGreater(rc["score"], 0)
        self.assertEqual(rc["bad_blocks"], st.tide - 1)  # no erosion on the winning tide
        self.assertEqual(dt.npc_say(st, c)[0], "win")


class TieInTest(unittest.TestCase):
    def test_caches_from_byte_spring_g39(self):
        with open(SPRING, encoding="utf-8") as f:
            spring = json.load(f)
        c = dt.load(DATA)
        files = dt.files_from_byte_spring(spring, c.block_kib)
        self.assertEqual(files, [{"id": f.id, "blocks": f.blocks, "priority": f.priority} for f in c.files])
        with self.assertRaises(dt.DefragError):
            dt.files_from_byte_spring(spring, 0)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dt.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--seed", "1", "--trace")
        self.assertEqual(code, 0)
        self.assertIn('"outcome": "won"', out)
        self.assertIn("WIN", out)
        code, out, _ = self.run_cli(DATA, "--idle", "--trace")
        self.assertEqual(code, 1)
        self.assertIn("FAIL tides_out", out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)
        self.assertIn("error", err)


if __name__ == "__main__":
    unittest.main()
