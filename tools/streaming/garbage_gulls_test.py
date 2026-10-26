# SPDX-License-Identifier: MIT
"""Tests for G120 Garbage Gulls."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import garbage_gulls as g  # noqa: E402

DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "garbage-gulls-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = g.validate(raw())
        self.assertEqual(c.npc_name, "Gullmother Brine")
        self.assertEqual(c.sweep_every, 6)

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["gulls"].update(fragments_per_save=101),
                    lambda d: d["gulls"].update(heap_cap=0),
                    lambda d: d["gulls"].update(sweep_every=-1),
                    lambda d: d["gulls"].update(windows=True),
                    lambda d: d["gulls"].pop("work_budget"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("sweep")):
            d = raw()
            mut(d)
            with self.assertRaises(g.GullError):
                g.validate(d)


class HeapTest(unittest.TestCase):
    def make(self):
        h = g.Heap()
        h.add_root("isle")
        a, b, c = h.alloc(), h.alloc(), h.alloc()
        h.link("isle", a)
        h.link(a, b)
        h.link(b, c)
        h.link(c, b)  # loop b <-> c
        return h, a, b, c

    def test_reachable_follows_links(self):
        h, a, b, c = self.make()
        self.assertEqual(h.reachable(), {a, b, c})

    def test_mark_sweep_frees_stranded_loop_only(self):
        h, a, b, c = self.make()
        h.unlink(a, 0)
        work = h.mark_sweep()
        self.assertEqual(h.objects, {a})
        self.assertEqual(work, 1 + 3)

    def test_refcount_leaks_loops(self):
        h, a, b, c = self.make()
        dst = h.unlink(a, 0)
        h.refcount_collect(dst)
        self.assertEqual(h.objects, {a, b, c})  # b <-> c keep each other alive

    def test_refcount_frees_acyclic_chain(self):
        h = g.Heap()
        h.add_root("isle")
        a, b = h.alloc(), h.alloc()
        h.link("isle", a)
        h.link(a, b)
        h.refcount_collect(h.unlink("isle", 0))
        self.assertEqual(h.objects, set())

    def test_sweep_never_frees_reachable(self):
        h, a, b, c = self.make()
        h.mark_sweep()
        self.assertEqual(h.objects, {a, b, c})


class GameTest(unittest.TestCase):
    def setUp(self):
        self.c = g.validate(raw())

    def test_tuned_interval_wins(self):
        for se in (5, 6, 7):
            r = g.simulate(self.c, se)
            self.assertEqual((r.status, r.windows_ok), (g.WON, self.c.windows), se)
            self.assertLessEqual(r.peak_heap, self.c.heap_cap)
            self.assertLessEqual(r.work, self.c.work_budget)

    def test_sweeping_too_often_burns_work(self):
        for se in (1, 2, 4):
            r = g.simulate(self.c, se)
            self.assertEqual((r.status, r.reason), (g.FAILED, g.FAIL_WORK), se)

    def test_sweeping_too_rarely_overflows(self):
        for se in (0, 8, 10):
            r = g.simulate(self.c, se)
            self.assertEqual((r.status, r.reason), (g.FAILED, g.FAIL_HEAP), se)

    def test_refcount_leaks_every_loop(self):
        r = g.simulate(self.c, refcount=True)
        self.assertEqual((r.status, r.reason, r.freed), (g.FAILED, g.FAIL_HEAP, 0))

    def test_refcount_works_without_loops(self):
        d = raw()
        d["gulls"]["fragments_per_save"] = 0
        r = g.simulate(g.validate(d), refcount=True)
        self.assertEqual(r.status, g.WON)
        self.assertGreater(r.freed, 0)

    def test_deterministic(self):
        self.assertEqual(g.simulate(self.c), g.simulate(self.c))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = g.islands_from_shoals(json.load(fh))
        c = g.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_win_and_traps(self):
        self.assertEqual(g.main([DATA]), 0)
        self.assertEqual(g.main([DATA, "--sweep-every", "1"]), 1)
        self.assertEqual(g.main([DATA, "--refcount"]), 1)

    def test_receipt_and_npc(self):
        c = g.validate(raw())
        rc = g.receipt(c, g.simulate(c), c.sweep_every, False)
        self.assertEqual((rc["quest"], rc["scheme"]), (g.QUEST_ID, "sweep_every_6"))
        self.assertTrue(g.npc_say(c, "storm").startswith("Gullmother Brine: "))


if __name__ == "__main__":
    unittest.main()
