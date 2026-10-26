# SPDX-License-Identifier: MIT
"""G59 Save Vault Keeper tests. Run: python -m unittest tools/streaming/save_vault_test.py -v"""
import copy
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import save_vault as sv  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "save-vault-v1.json")
SPRING = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(**over):
    r = raw()
    r.update(over)
    return sv.validate(r)


def idle(state, config):
    return []


class ValidateTest(unittest.TestCase):
    def test_shipped_data_valid(self):
        c = sv.load(DATA)
        self.assertEqual(c.quota_kib, 600)
        self.assertEqual(len(c.islands), 3)
        self.assertEqual(c.npc_name, "Archivist Ledger")

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(sv.VaultError):
            sv.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_other"))
        self.bad(lambda r: r["vault"].update(quota_kib=0))
        self.bad(lambda r: r["vault"].update(quota_kib=True))
        self.bad(lambda r: r["vault"].pop("mirror_kib_per_tick"))
        self.bad(lambda r: r["islands"].append(copy.deepcopy(r["islands"][0])))
        self.bad(lambda r: r["islands"][0].update(id="bad id"))
        self.bad(lambda r: r["islands"][0].update(chunks_per_snapshot=999))
        self.bad(lambda r: r["islands"][0].update(write_permille=1001))
        self.bad(lambda r: r.update(islands=[]))
        self.bad(lambda r: r.update(win_ticks=0))
        self.bad(lambda r: r["npc"]["lines"].pop("win"))
        self.bad(lambda r: r["npc"]["lines"].update(win=""))
        self.bad(lambda r: r["vault"].update(quota_kib=10))  # pinned set alone overflows
        self.bad(lambda r: r.update(npc="x"))


class RulesTest(unittest.TestCase):
    def test_start_one_snapshot_per_island_all_pinned(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        self.assertEqual(len(st.snaps), 3)
        self.assertEqual(st.pinned(), set(st.snaps))
        self.assertEqual(sv.used_kib(st, c), 8 * 6 + 6 * 5 + 12 * 4)

    def test_dedupe_shared_chunks_counted_once(self):
        c = cfg(islands=[{"id": "a", "chunk_kib": 10, "pool": 8, "chunks_per_snapshot": 4,
                          "write_permille": 1000, "churn_permille": 0}])
        st = sv.new_state(c)
        sv.tick(st, c, [])
        self.assertEqual(len(st.snaps), 2)
        self.assertEqual(sv.used_kib(st, c), 40)  # identical chunks shelved once

    def test_pinned_newest_refused(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        sid = sorted(st.snaps)[0]
        sv.tick(st, c, [("prune", sid)])
        self.assertIn(sid, st.snaps)
        self.assertIn("pinned", st.events)
        self.assertEqual(st.outcome, sv.RUNNING)

    def test_prune_unmirrored_loses_work(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        for _ in range(5):
            sv.tick(st, c, [])
        old = [s for s in st.snaps if s not in st.pinned()]
        self.assertTrue(old)
        sv.tick(st, c, [("prune", old[0])])
        self.assertEqual((st.outcome, st.fail_reason), (sv.FAILED, sv.FAIL_LOST))
        self.assertEqual(sv.npc_say(st, c)[0], "fail_lost")

    def test_mirror_then_prune_is_safe(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        first = sorted(st.snaps)[0]
        sv.tick(st, c, [("mirror", first)])
        while not st.snaps[first].mirrored:
            sv.tick(st, c, [])
        while first in st.pinned():
            sv.tick(st, c, [])
            if st.outcome != sv.RUNNING:
                self.skipTest("seeded run ended before the island wrote again")
        sv.tick(st, c, [("prune", first)])
        self.assertNotIn(first, st.snaps)
        self.assertIn(first, st.pruned)
        self.assertEqual(st.outcome, sv.RUNNING)

    def test_bandwidth_limits_upload(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        sv.tick(st, c, [("mirror", s) for s in sorted(st.snaps)])
        self.assertLessEqual(st.uploaded_kib, c.mirror_kib_per_tick)
        self.assertTrue(st.queue)

    def test_idle_keeper_overflows_seeds_1_to_20(self):
        for seed in range(1, 21):
            st = sv.simulate(cfg(seed=seed), idle)
            self.assertEqual((st.outcome, st.fail_reason), (sv.FAILED, sv.FAIL_QUOTA), seed)

    def test_bad_actions(self):
        c = sv.load(DATA)
        st = sv.new_state(c)
        with self.assertRaises(sv.VaultError):
            sv.tick(st, c, [("burn", "x")])
        with self.assertRaises(sv.VaultError):
            sv.tick(st, c, [("prune", "nope")])

    def test_over_is_over(self):
        st = sv.simulate(sv.load(DATA))
        with self.assertRaises(sv.VaultError):
            sv.tick(st, sv.load(DATA), [])


class SeededTest(unittest.TestCase):
    def test_keeper_wins_and_greedy_loses_seeds_1_to_20(self):
        for seed in range(1, 21):
            c = cfg(seed=seed)
            good = sv.simulate(c)
            self.assertEqual(good.outcome, sv.WON, seed)
            self.assertLessEqual(sv.used_kib(good, c), c.quota_kib)
            for s in good.pinned():
                self.assertIn(s, good.snaps)
            bad = sv.simulate(c, sv.greedy_policy)
            self.assertEqual(bad.fail_reason, sv.FAIL_LOST, seed)

    def test_deterministic_trace(self):
        a = sv.simulate(cfg(seed=7)).log
        b = sv.simulate(cfg(seed=7)).log
        self.assertEqual(a, b)
        self.assertNotEqual(a, sv.simulate(cfg(seed=8)).log)

    def test_lcg_golden(self):
        r = sv.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_receipt_shape(self):
        c = sv.load(DATA)
        st = sv.simulate(c)
        rc = sv.receipt(st, c)
        self.assertEqual(rc["quest"], "q_save_vault")
        self.assertEqual(rc["outcome"], "won")
        self.assertGreater(rc["score"], 0)
        self.assertEqual(rc["ticks"], c.win_ticks)
        self.assertEqual(sv.npc_say(st, c)[0], "win")


class TieInTest(unittest.TestCase):
    def test_quota_from_byte_spring_g39(self):
        with open(SPRING, encoding="utf-8") as f:
            spring = json.load(f)
        q = sv.quota_from_byte_spring(spring)
        self.assertEqual(q, spring["cistern"]["budget_cap"])
        self.assertEqual(q, sv.load(DATA).quota_kib)  # shipped vault uses the G39 cap
        self.assertEqual(sv.quota_from_byte_spring(spring, 4), q * 4)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sv.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--seed", "1")
        self.assertEqual(code, 0)
        self.assertIn('"outcome": "won"', out)
        code, out, _ = self.run_cli(DATA, "--greedy", "--trace")
        self.assertEqual(code, 1)
        self.assertIn("FAIL lost_unmirrored", out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)
        self.assertIn("error", err)


if __name__ == "__main__":
    unittest.main()
