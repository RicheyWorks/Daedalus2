# SPDX-License-Identifier: MIT
"""The Java day book (daedalus-core com.daedalus.world.colony) replays a fixture made from these Python cores.
This test fails if colony_ledger.py / island_chemistry.py changed without regenerating it, so Java and Python
cannot drift apart silently."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daybook_parity as P  # noqa: E402


class DayBookParityFixture(unittest.TestCase):
    def test_fixture_is_current(self):
        with open(P.OUT, encoding="utf-8") as f:
            self.assertEqual(f.read(), P.render(), "run: python tools/economy/daybook_parity.py")

    def test_fixture_covers_the_interesting_cases(self):
        text = P.render()
        self.assertEqual(text.count("\nCASE\t"), len(P.CASES))
        self.assertIn("Portal_KingsRoad", text)               # a PORT09 quest giver shows up on the news board
        self.assertTrue(any(r.split("\t")[4] == "1" for r in text.splitlines() if r.startswith("CASE")))  # crater island


if __name__ == "__main__":
    unittest.main()
