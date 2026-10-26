# SPDX-License-Identifier: MIT
"""G76 Driftwood Codes tests. Run: python -m unittest tools/streaming/driftwood_codes_test.py -v"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import driftwood_codes as dc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "driftwood-codes-v1.json")
TIDE = os.path.join(ROOT, "data", "islands", "disk-saver", "tide-chart-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def cfg(**over):
    r = raw()
    r.update(over)
    return dc.validate(r)


class ValidateTest(unittest.TestCase):
    def test_shipped(self):
        c = dc.load(DATA)
        self.assertEqual(len(c.kinds), 8)
        self.assertEqual(c.bit_budget, 280)

    def bad(self, mutate):
        r = raw()
        mutate(r)
        with self.assertRaises(dc.CodeError):
            dc.validate(r)

    def test_rejects(self):
        self.bad(lambda r: r.update(v=2))
        self.bad(lambda r: r.update(extra=1))
        self.bad(lambda r: r.update(quest="q_x"))
        self.bad(lambda r: r.update(kinds=r["kinds"][:1]))
        self.bad(lambda r: r["kinds"].append(dict(r["kinds"][0])))
        self.bad(lambda r: r["kinds"][0].update(freq=0))
        self.bad(lambda r: r["kinds"][0].update(id="a b"))
        self.bad(lambda r: r.update(bit_budget=258))  # below the optimum (259)
        self.bad(lambda r: r["npc"]["lines"].pop("win"))


class RulesTest(unittest.TestCase):
    def test_huffman_hits_optimum_and_wins(self):
        c = dc.load(DATA)
        st = dc.simulate(c)
        self.assertEqual(st.bits, dc.optimal_bits(c))
        self.assertEqual(st.bits, 259)
        self.assertEqual(st.outcome, dc.WON)
        self.assertEqual(st.ties, len(c.kinds) - 1)

    def test_in_order_trap_fails(self):
        c = dc.load(DATA)
        st = dc.simulate(c, dc.in_order_pair)
        self.assertEqual((st.outcome, st.fail_reason), (dc.FAILED, dc.FAIL_BITS))
        self.assertGreater(st.bits, c.bit_budget)
        self.assertEqual(dc.npc_say(st, c)[0], "fail")

    def test_codes_prefix_free_kraft_and_round_trip(self):
        c = dc.load(DATA)
        st = dc.simulate(c)
        cm = dc.codes(st)
        self.assertTrue(dc.kraft_ok(dc.code_lengths(st)))
        vals = list(cm.values())
        for a in vals:
            for b in vals:
                if a != b:
                    self.assertFalse(b.startswith(a))
        msg = [k for k, f in c.kinds for _ in range(f)]
        bits = dc.encode(cm, msg)
        self.assertEqual(len(bits), st.bits)
        self.assertEqual(dc.decode(cm, bits), msg)
        with self.assertRaises(dc.CodeError):
            dc.decode(cm, bits + "1")

    def test_frequent_kinds_get_short_codes(self):
        st = dc.simulate(dc.load(DATA))
        lens = dc.code_lengths(st)
        self.assertEqual(lens["tile"], 1)
        self.assertGreaterEqual(lens["fx"], lens["mesh"])

    def test_light_and_heavy_barks(self):
        c = dc.load(DATA)
        st = dc.new_state(c)
        dc.tie(st, c, *dc.lightest_pair(st))
        self.assertIn("light", st.events)
        dc.tie(st, c, *dc.in_order_pair(st))  # tile + mesh: heavy
        self.assertIn("heavy", st.events)

    def test_tie_errors(self):
        c = dc.load(DATA)
        st = dc.new_state(c)
        with self.assertRaises(dc.CodeError):
            dc.tie(st, c, 0, 0)
        with self.assertRaises(dc.CodeError):
            dc.tie(st, c, 0, 99)
        with self.assertRaises(dc.CodeError):
            dc.code_lengths(st)
        done = dc.simulate(c)
        with self.assertRaises(dc.CodeError):
            dc.tie(done, c, 0, 1)

    def test_two_kinds(self):
        r = raw()
        r["kinds"] = [{"id": "a", "freq": 3}, {"id": "b", "freq": 1}]
        r["bit_budget"] = 4
        st = dc.simulate(dc.validate(r))
        self.assertEqual((st.bits, st.outcome), (4, dc.WON))

    def test_receipt(self):
        c = dc.load(DATA)
        rc = dc.receipt(dc.simulate(c), c)
        self.assertEqual((rc["quest"], rc["activity"], rc["outcome"], rc["score"]),
                         ("q_driftwood_codes", "driftwood_codes", "won", 1000))


class TieInTest(unittest.TestCase):
    def test_freqs_from_tide_chart(self):
        with open(TIDE, encoding="utf-8") as f:
            tide = json.load(f)
        kinds = dc.freqs_from_tide_chart(tide)
        self.assertEqual(sum(k["freq"] for k in kinds), tide["pool"]["tides"])
        r = raw()
        r["kinds"] = kinds
        r["bit_budget"] = 2 * tide["pool"]["tides"]  # fixed 2-bit ids for 3 islands
        c = dc.validate(r)
        self.assertLess(dc.simulate(c).bits, c.bit_budget)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dc.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        code, out, _ = self.run_cli(DATA, "--trace")
        self.assertEqual(code, 0)
        self.assertIn('"tile": "0"', out)
        code, out, _ = self.run_cli(DATA, "--in-order")
        self.assertEqual(code, 1)
        code, _, err = self.run_cli(os.path.join(HERE, "missing.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
