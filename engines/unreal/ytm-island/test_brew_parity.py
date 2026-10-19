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


if __name__ == "__main__":
    unittest.main()
