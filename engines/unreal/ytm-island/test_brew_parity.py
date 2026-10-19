# SPDX-License-Identifier: MIT
"""Java Melody Brewing (daedalus-core com.daedalus.world.brew) replays a fixture made from herbcombo.py; fail if stale."""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brew_parity as P  # noqa: E402
import herbcombo as H  # noqa: E402


class BrewParity(unittest.TestCase):
    def test_fixture_is_current(self):
        self.assertEqual(subprocess.call([sys.executable, os.path.join(HERE, "brew_parity.py"), "--check"]), 0)

    def test_fixture_covers_every_contour_and_cadence(self):
        text = P.render()
        for m in ("Rise", "Fall", "Arch", "Valley", "Dance", "Noise", "Cadence"):
            self.assertIn("\t" + m, text.replace(" Cadence", "\tCadence"))

    def test_found_tunes_brew_as_their_csv_says(self):
        with open(P.TUNES_SRC, encoding="utf-8") as f:
            for line in f.read().splitlines()[1:]:
                c = line.split(",")
                herbs = c[2].split("|")
                r = H.brew([(h, 3) for h in herbs])
                self.assertEqual(r["melody"], c[4], c[0])
                self.assertEqual(r["notes"], [int(n) for n in c[3].split("|")], c[0])

class NativeTierRounding(unittest.TestCase):
    """ADaedalusBrewBench (DaedalusHomestead.cpp) must round the stage average half-to-even like herbcombo/Java.
    Editor run 2026-10-19: FMath::RoundToInt made 27/1935 parity rows one tier too high (every 2.5 average)."""
    CPP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "unreal", "DaedalusLink", "Source", "DaedalusLink", "Private",
                       "DaedalusHomestead.cpp")

    def test_python_reference_ties(self):
        self.assertEqual(H.brew([("Mimint", 3), ("Sharpcress", 4), ("Flatfern", 1), ("Dronebloom", 2)])["tier"], 2)
        self.assertEqual(round(3.5), 4)

    def test_native_tier_uses_half_to_even(self):
        with open(self.CPP, encoding="utf-8") as f:
            line = next(l for l in f if "R.Tier = " in l and "StageSum" in l)
        self.assertIn("RoundHalfToEven", line)
        self.assertNotIn("RoundToInt", line)


if __name__ == "__main__":
    unittest.main()
