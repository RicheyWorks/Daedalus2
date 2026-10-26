# SPDX-License-Identifier: MIT
"""G70 Tide Chart Cache tests. Run: python -m unittest tools/streaming/tide_chart_cache_test.py -v"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tide_chart_cache as tc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "tide-chart-v1.json")
SPRING = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(seed=None, **pool):
    r = raw()
    r["pool"].update(pool)
    if seed is not None:
        r["seed"] = seed
    return tc.validate(r)


class ValidateTest(unittest.TestCase):
    def test_shipped(self):
        c = tc.load(DATA)
        self.assertEqual((c.capacity_kib, c.tides, c.chart_len, c.stall_budget_kib), (480, 60, 8, 3000))
        self.assertEqual([i.id for i in c.islands], ["cache_north", "cache_south", "vault_east"])

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(tc.CacheError):
            tc.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r["pool"].pop("chart_len"))
        self.bad(lambda r: r["pool"].update(capacity_kib=0))
        self.bad(lambda r: r["pool"].update(capacity_kib=10_000))  # no pressure
        self.bad(lambda r: r["islands"][0].update(cost_kib=10_000))  # larger than the pool
        self.bad(lambda r: r["islands"][0].update(weight=0))
        self.bad(lambda r: r["islands"].append(dict(r["islands"][0])))
        self.bad(lambda r: r.update(islands=r["islands"][:1]))
        self.bad(lambda r: r["npc"]["lines"].pop("evict"))


class RulesTest(unittest.TestCase):
    def test_requests_seeded_and_weighted(self):
        c = cfg(tides=3000)
        a = tc.requests(c)
        self.assertEqual(a, tc.requests(c))
        self.assertNotEqual(a, tc.requests(cfg(2, tides=3000)))
        counts = {i.id: a.count(i.id) for i in c.islands}
        self.assertGreater(counts["vault_east"], counts["cache_north"])  # weight 3 vs 2
        self.assertGreater(counts["cache_north"], counts["cache_south"])  # weight 2 vs 1

    def test_hits_misses_and_capacity(self):
        c = tc.load(DATA)
        st = tc.new_state(c)
        while st.outcome == tc.RUNNING:
            tc.step(st, c, tc.chart_policy)
            self.assertLessEqual(tc.used_kib(st, c), c.capacity_kib)
        self.assertEqual(st.hits + st.misses, c.tides)
        self.assertGreater(st.evictions, 0)

    def test_stall_is_sum_of_miss_costs(self):
        c = cfg(stall_budget_kib=10**8)
        st = tc.simulate(c, tc.lru_policy)
        self.assertEqual(st.stall_kib, sum(c.cost(line.split()[2]) for line in st.log if " miss " in line))

    def test_bad_policy_rejected(self):
        c = tc.load(DATA)
        st = tc.new_state(c)
        with self.assertRaises(tc.CacheError):
            while True:
                tc.step(st, c, lambda s, cf, need: "nowhere")

    def test_chart_policy_reads_the_chart(self):
        c = cfg(chart_len=3)
        st = tc.new_state(c)
        st.reqs = ["cache_north", "vault_east", "cache_south", "vault_east", "cache_north"]
        st.resident = ["cache_north", "vault_east"]
        st.tide = 1
        # chart after tide 1: cache_south, vault_east, cache_north -> north is needed last
        self.assertEqual(tc.chart_policy(st, c, "cache_south"), "cache_north")

    def test_over_is_over(self):
        c = tc.load(DATA)
        st = tc.simulate(c)
        with self.assertRaises(tc.CacheError):
            tc.step(st, c, tc.chart_policy)


class SeededTest(unittest.TestCase):
    def test_chart_never_worse_than_lru_seeds_1_to_40(self):
        for s in range(1, 41):
            c = cfg(s, stall_budget_kib=10**8)
            self.assertLessEqual(tc.simulate(c).stall_kib, tc.simulate(c, tc.lru_policy).stall_kib, s)

    def test_chart_wins_more_than_lru(self):
        chart = sum(tc.simulate(cfg(s)).outcome == tc.WON for s in range(1, 41))
        lru = sum(tc.simulate(cfg(s), tc.lru_policy).outcome == tc.WON for s in range(1, 41))
        self.assertGreaterEqual(chart, 38)
        self.assertLess(lru, chart)

    def test_seed_1_win_receipt(self):
        c = tc.load(DATA)
        st = tc.simulate(c)
        rc = tc.receipt(st, c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"]), ("q_tide_chart", "tide_chart_cache", "won"))
        self.assertGreater(rc["score"], 0)
        self.assertEqual(tc.npc_say(st, c)[0], "win")

    def test_lcg_golden(self):
        r = tc.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])


class TieInTest(unittest.TestCase):
    def test_config_from_byte_spring_g39(self):
        with open(SPRING, encoding="utf-8") as f:
            spring = json.load(f)
        r = raw()
        built = tc.config_from_byte_spring(spring, 60, 8, 3000, r["npc"], 1)
        self.assertEqual(built["pool"], r["pool"])
        self.assertEqual(built["islands"], r["islands"])
        self.assertEqual(tc.validate(built), tc.load(DATA))


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = tc.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--seed", "1", "--trace")
        self.assertEqual(code, 0)
        self.assertIn("WIN", out)
        code, out, _ = self.run_cli(DATA, "--lru")
        self.assertIn('"activity": "tide_chart_cache"', out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
