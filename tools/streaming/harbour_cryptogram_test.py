# SPDX-License-Identifier: MIT
"""Tests for harbour_cryptogram (G552)."""
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import harbour_cryptogram as hc  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "harbour-cryptogram-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "title": t, "assets": [{"name": a} for a in assets],
                        "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]}
                       for w, t, assets, isl in worlds]}


DOC = census([("alpha", "Isle of Rain-2", ["ark", "beacon", "crane"], [(1, 0), (2, 3)]),
              ("beta", "", [], [(4, 0)])])


class CryptogramTest(unittest.TestCase):
    def test_number_words(self):
        self.assertEqual(hc.number_words(0), "ZERO")
        self.assertEqual(hc.number_words(21), "TWENTY ONE")
        self.assertEqual(hc.number_words(40), "FORTY")
        self.assertEqual(hc.number_words(305), "THREE HUNDRED AND FIVE")
        self.assertEqual(hc.number_words(1200), "ONE TWO ZERO ZERO")

    def test_facts_are_true(self):
        f = hc.facts(DOC)
        self.assertIn("ISLE OF RAIN CHARTS TWO ISLANDS", f)
        self.assertIn("ISLE OF RAIN CARRIES ARK AND BEACON AND CRANE", f)
        self.assertIn("ISLE OF RAIN HAS ONE EMPTY ISLAND", f)
        self.assertIn("BETA CHARTS ONE ISLAND", f)
        self.assertEqual(f[-1], "THE HARBOUR HOLDS THREE ISLANDS IN TWO WORLDS")
        self.assertTrue(all(set(s) <= set(hc.ALPHA + " ") for s in f))

    def test_derangement(self):
        rng = random.Random(1)
        for _ in range(50):
            k = hc.derangement(rng)
            self.assertEqual(sorted(k.values()), list(hc.ALPHA))
            self.assertTrue(all(a != b for a, b in k.items()))

    def test_cipher_round_trip(self):
        for s in range(10):
            p = hc.make(DOC, s)
            self.assertEqual("".join(p["key"].get(ch, ch) for ch in p["cipher"]), p["plain"])
            self.assertEqual(len(p["cipher"]), len(p["plain"]))
            self.assertEqual([i for i, c in enumerate(p["cipher"]) if c == " "], [i for i, c in enumerate(p["plain"]) if c == " "])

    def test_plain_from_facts(self):
        p = hc.make(DOC, 3)
        parts = p["plain"].split(" STOP ")
        self.assertLessEqual(len(parts), hc.MAX_SENTENCES)
        self.assertTrue(set(parts) <= set(hc.facts(DOC)))

    def test_givens_consistent_and_partial(self):
        p = hc.make(DOC, 2)
        self.assertGreaterEqual(len(p["given"]), 2)
        for c, v in p["given"].items():
            self.assertEqual(p["key"][c], v)
        self.assertLess(len(p["given"]), len(p["key"]))
        self.assertEqual(sum(p["frequency"].values()), sum(1 for ch in p["cipher"] if ch != " "))

    def test_seeded(self):
        self.assertEqual(hc.make(DOC, 5), hc.make(DOC, 5))
        self.assertGreater(len({hc.make(DOC, s)["cipher"] for s in range(8)}), 4)

    def test_grade(self):
        p = hc.make(DOC, 1)
        self.assertEqual(hc.grade(p, p["plain"].lower())["verdict"], "decoded")
        half = "".join(ch if i % 3 else "Q" for i, ch in enumerate(p["plain"]))
        self.assertEqual(hc.grade(p, half)["verdict"], "partial")
        self.assertEqual(hc.grade(p, "nothing like it")["verdict"], "garbled")
        self.assertEqual(hc.grade(p, p["plain"] + " EXTRA")["verdict"], "partial")

    def test_mapping(self):
        p = hc.make(DOC, 4)
        full = hc.apply_mapping(p, {c.lower(): v for c, v in p["key"].items()})
        self.assertEqual(full, p["plain"])
        given_only = hc.apply_mapping(p, {})
        self.assertIn("?", given_only)
        for bad in ({"AB": "C"}, {"A": "1"}, ["A"]):
            with self.assertRaises(hc.CryptogramError):
                hc.apply_mapping(p, bad)

    def test_refusals(self):
        with self.assertRaises(hc.CryptogramError):
            hc.make({"format": "nope"})
        with self.assertRaises(hc.CryptogramError):
            hc.number_words(-1)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(hc.main([c, "--json"]), 0)
            pub = json.loads(out.getvalue())
            self.assertNotIn("plain", pub)
            self.assertNotIn("key", pub)
            p = hc.make(DOC, 0)
            m = os.path.join(d, "key.json")
            with open(m, "w", encoding="utf-8") as f:
                json.dump(p["key"], f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(hc.main([c, "--mapping", m]), 0)
            self.assertTrue(out.getvalue().startswith("harbour cryptogram: decoded"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(hc.main([c, "--guess", "x"]), 0)
            self.assertIn("garbled", out.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(hc.main([os.path.join(d, "none.json")]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        f = hc.facts(doc)
        self.assertIn("SYNTHETIC ALPHA CARRIES ARK AND BEACON", f)
        self.assertIn("THE HARBOUR HOLDS THREE ISLANDS IN TWO WORLDS", f)
        p = hc.make(doc, 0)
        self.assertEqual(hc.grade(p, p["plain"])["verdict"], "decoded")

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_harbour_cryptogram")
        self.assertEqual(h["npc"]["name"], "Telegraphist Philippa")
        self.assertEqual(h["hook"]["values"], list(hc.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
