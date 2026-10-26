# SPDX-License-Identifier: MIT
"""G78 Coral Wear tests. Run: python -m unittest tools/streaming/coral_wear_test.py -v"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coral_wear as cw  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "coral-wear-v1.json")
TIDE = os.path.join(ROOT, "data", "islands", "disk-saver", "tide-chart-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(seed=None, **coral):
    r = raw()
    r["coral"].update(coral)
    if seed is not None:
        r["seed"] = seed
    return cw.validate(r)


def wins(policy, **coral):
    return sum(cw.simulate(cfg(s, **coral), policy).outcome == cw.WON for s in range(1, 41))


class ValidateTest(unittest.TestCase):
    def test_shipped(self):
        c = cw.load(DATA)
        self.assertEqual((c.cells, c.endurance_min, c.endurance_max, c.season_ticks), (9, 20, 30, 160))
        self.assertEqual(len(c.islands), 6)

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(cw.WearError):
            cw.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r["coral"].update(cells=6))  # no spare cell
        self.bad(lambda r: r["coral"].update(endurance_max=5))  # below min
        self.bad(lambda r: r["coral"].pop("season_ticks"))
        self.bad(lambda r: r["islands"][0].update(weight=0))
        self.bad(lambda r: r["islands"].append(dict(r["islands"][0])))
        self.bad(lambda r: r["npc"]["lines"].pop("retire"))


class RulesTest(unittest.TestCase):
    def test_start(self):
        c = cw.load(DATA)
        st = cw.new_state(c)
        self.assertEqual(len(st.free_cells()), 3)
        self.assertTrue(all(c.endurance_min <= e <= c.endurance_max for e in st.endurance))
        self.assertIn(st.pending, dict(c.islands))

    def test_write_moves_save_and_wears_target(self):
        c = cw.load(DATA)
        st = cw.new_state(c)
        iid, old = st.pending, st.home[st.pending]
        tgt = st.free_cells()[0]
        cw.tick(st, c, tgt)
        self.assertEqual(st.home[iid], tgt)
        self.assertIsNone(st.holder[old])
        self.assertEqual(st.wear[tgt], 1)
        self.assertEqual(st.wear[old], 0)

    def test_bad_targets(self):
        c = cw.load(DATA)
        st = cw.new_state(c)
        with self.assertRaises(cw.WearError):
            cw.tick(st, c, 0)  # held
        with self.assertRaises(cw.WearError):
            cw.tick(st, c, 99)
        with self.assertRaises(cw.WearError):
            cw.tick(cw.new_state(c), c, 6, ("nobody", 7))

    def test_retired_cell_never_free(self):
        c = cw.load(DATA)
        st = cw.new_state(c)
        st.wear[6] = st.endurance[6]
        self.assertNotIn(6, st.free_cells())

    def test_relocation_frees_cold_cell(self):
        c = cw.load(DATA)
        st = cw.new_state(c)
        cold = next(i for i, _ in c.islands if i.startswith("archive") and i != st.pending)
        src = st.home[cold]
        cw.tick(st, c, 7, (cold, 6))
        self.assertEqual(st.home[cold], 6)
        self.assertIn(src, st.free_cells())
        self.assertEqual(st.relocations, 1)
        self.assertIn("relocate", st.events)

    def test_over_is_over(self):
        c = cw.load(DATA)
        st = cw.simulate(c)
        with self.assertRaises(cw.WearError):
            cw.tick(st, c, st.free_cells()[0])


class SeededTest(unittest.TestCase):
    def test_static_leveling_wins_seeds_1_to_40(self):
        self.assertEqual(wins(cw.leveling_policy), 40)

    def test_policy_ladder(self):
        lev, lw, ff = wins(cw.leveling_policy), wins(cw.least_worn_policy), wins(cw.first_free_policy)
        self.assertGreater(lev, lw)
        self.assertGreater(lw, ff)

    def test_endless_season_always_ends_in_bleach(self):
        st = cw.simulate(cfg(1, season_ticks=10**6))
        self.assertEqual((st.outcome, st.fail_reason), (cw.FAILED, cw.FAIL_FULL))
        self.assertLessEqual(st.writes + st.relocations, sum(st.endurance))
        self.assertEqual(cw.npc_say(st, cw.load(DATA))[0], "fail")

    def test_deterministic_and_lcg_golden(self):
        self.assertEqual(cw.simulate(cfg(4)).log, cw.simulate(cfg(4)).log)
        r = cw.Lcg(1)
        self.assertEqual([r.next() for _ in range(3)], [1015568748, 1586005467, 2165703038])

    def test_receipt(self):
        c = cw.load(DATA)
        st = cw.simulate(c)
        rc = cw.receipt(st, c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"]), ("q_coral_wear", "coral_wear", "won"))
        self.assertEqual(rc["writes"], c.season_ticks)
        self.assertGreater(rc["score"], 0)


class TieInTest(unittest.TestCase):
    def test_islands_from_tide_chart_g70(self):
        with open(TIDE, encoding="utf-8") as f:
            tide = json.load(f)
        self.assertEqual(cw.islands_from_tide_chart(tide), raw()["islands"])


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cw.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--trace")
        self.assertEqual(code, 0)
        self.assertIn("WIN", out)
        code, out, _ = self.run_cli(DATA, "--policy", "first_free", "--seed", "1")
        self.assertIn('"activity": "coral_wear"', out)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
