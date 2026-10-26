# SPDX-License-Identifier: MIT
"""Tests for G113 Snapshot Shells."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import snapshot_shells as s  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "snapshot-shells-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = s.validate(raw())
        self.assertEqual(c.npc_name, "Shellwright Marrow")
        self.assertEqual((c.keep, c.restore_depth), (8, 8))

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["shells"].update(keep=-1),
                    lambda d: d["shells"].update(restore_depth=0),
                    lambda d: d["shells"].update(restore_permille=1001),
                    lambda d: d["shells"].update(windows=True),
                    lambda d: d["shells"].pop("space_budget"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("press")):
            d = raw()
            mut(d)
            with self.assertRaises(s.ShellError):
                s.validate(d)


class StoreTest(unittest.TestCase):
    def test_cow_shares_unchanged_blocks(self):
        st = s.ShellStore(3)
        live = {"a": 0, "b": 0, "c": 0}
        st.press(live)
        live["a"] = 1
        st.press(live)
        self.assertEqual(st.space(live), 4)  # a0 a1 b0 c0

    def test_full_copy_pays_every_block(self):
        st = s.ShellStore(3, full_copy=True)
        live = {"a": 0, "b": 0}
        st.press(live)
        st.press(live)
        self.assertEqual(st.space(live), 6)

    def test_keep_prunes_oldest_and_restore_ages(self):
        st = s.ShellStore(2)
        for v in range(4):
            st.press({"a": v})
        self.assertEqual(st.restore(1), {"a": 3})
        self.assertEqual(st.restore(2), {"a": 2})
        self.assertIsNone(st.restore(3))
        self.assertIsNone(st.restore(0))

    def test_restore_is_a_copy(self):
        st = s.ShellStore(1)
        live = {"a": 0}
        st.press(live)
        live["a"] = 5
        got = st.restore(1)
        got["a"] = 9
        self.assertEqual(st.restore(1), {"a": 0})

    def test_keep_zero_and_keep_all(self):
        none, every = s.ShellStore(0), s.ShellStore(-1)
        for v in range(5):
            none.press({"a": v})
            every.press({"a": v})
        self.assertIsNone(none.restore(1))
        self.assertEqual(every.restore(5), {"a": 0})


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = s.validate(raw())

    def test_tuned_keep_wins(self):
        for k in (8, 9):
            r = s.simulate(self.c, k)
            self.assertEqual((r.status, r.windows_ok), (s.WON, self.c.windows), k)
            self.assertEqual(r.restores, r.restores_ok)
            self.assertGreater(r.restores, 0)

    def test_too_few_shells_cannot_restore(self):
        for k in (0, 4, 7):
            r = s.simulate(self.c, k)
            self.assertEqual((r.status, r.reason), (s.FAILED, s.FAIL_RESTORE), k)

    def test_keep_all_and_full_copy_overflow(self):
        for kw in ({"keep": -1}, {"keep": 10}, {"full_copy": True}):
            r = s.simulate(self.c, **kw)
            self.assertEqual((r.status, r.reason), (s.FAILED, s.FAIL_SPACE), kw)
        self.assertGreater(s.simulate(self.c, full_copy=True).worst_space,
                           5 * s.simulate(self.c).worst_space)

    def test_deterministic(self):
        self.assertEqual(s.simulate(self.c), s.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = s.islands_from_shoals(json.load(fh))
        c = s.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(s.main([DATA]), 0)
        self.assertEqual(s.main([DATA, "--keep", "-1"]), 1)
        self.assertEqual(s.main([DATA, "--full-copy"]), 1)

    def test_receipt_and_npc(self):
        c = s.validate(raw())
        rc = s.receipt(c, s.simulate(c), c.keep, False)
        self.assertEqual(rc["quest"], s.QUEST_ID)
        self.assertTrue(s.npc_say(c, "restore").startswith("Shellwright Marrow: "))


if __name__ == "__main__":
    unittest.main()
