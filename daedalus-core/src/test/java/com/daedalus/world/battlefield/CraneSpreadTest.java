// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.CraneSpread.Report;
import com.daedalus.world.battlefield.CraneSpread.Settings;
import org.junit.jupiter.api.Test;

class CraneSpreadTest {

    private static final Settings D = Settings.DEFAULT;

    @Test
    void kernelIsANormalisedLaplace() {
        CraneSpread m = CraneSpread.marsh(D, 1);
        assertEquals(1.0, m.mgf(0), 1e-12);
        // Discretised Laplace MGF is close to the continuous 1 / (1 - b^2 s^2).
        assertEquals(1 / (1 - 0.25), m.mgf(0.5), 0.02);
        assertTrue(m.mgf(0.5) > m.mgf(0.25));
    }

    @Test
    void spreadingSpeedIsTheMinimumOfTheDispersionCurve() {
        CraneSpread m = CraneSpread.marsh(D, 1);
        double c = m.spreadingSpeed();
        double lam = D.lambda();
        for (double s = 0.01; s < 0.999; s += 0.01) {
            assertTrue(Math.log(lam * m.mgf(s)) / s >= c - 1e-9);
        }
        assertEquals(1.38303, c, 1e-3);
        // Speed scales with dispersal distance (b 2 roughly doubles it) and grows with lambda.
        double c2 = CraneSpread.marsh(new Settings(1.5, 2.0, 0.25, 100, 50), 1).spreadingSpeed();
        assertEquals(2 * c, c2, 0.05 * c);
        assertTrue(CraneSpread.marsh(new Settings(2.0, 1.0, 0.25, 100, 50), 1).spreadingSpeed() > c);
    }

    @Test
    void frontApproachesSpreadingSpeedFromBelow() {
        Settings[] all = {D, new Settings(1.5, 2.0, 0.25, 100, 200), new Settings(2.0, 0.5, 0.25, 100, 200)};
        for (Settings s : all) {
            CraneSpread m = CraneSpread.marsh(s, 1);
            double c = m.spreadingSpeed();
            double v = m.run().speed();
            assertTrue(v <= c * 1.005, v + " > " + c);
            assertEquals(c, v, 0.03 * c, s.toString());
        }
    }

    @Test
    void decliningFlocksDoNotSpread() {
        CraneSpread m = CraneSpread.marsh(new Settings(0.95, 1.0, 0.25, 100, 100), 1);
        assertEquals(0, m.spreadingSpeed(), 0);
        Report r = m.run();
        assertTrue(r.years().get(100).front() <= (CraneSpread.SOURCE + 4) * 0.25);
        assertEquals(-1, r.yearReached(20));
    }

    @Test
    void noisyFrontTracksTheDeterministicOne() {
        CraneSpread m = CraneSpread.marsh(D, 5);
        double det = m.run().speed();
        double sum = 0;
        for (long seed = 1; seed <= 5; seed++) {
            sum += m.run(seed).speed();
        }
        assertEquals(det, sum / 5, 0.15 * det);
    }

    @Test
    void seededRunsReplay() {
        Settings s = new Settings(1.5, 1.0, 0.25, 30, 60);
        Report a = CraneSpread.marsh(s, 9).runNoisy();
        assertEquals(a, CraneSpread.marsh(s, 9).runNoisy());
        assertEquals(a, CraneSpread.marsh(s, 1).run(9));
        assertNotEquals(a.years(), CraneSpread.marsh(s, 1).run(10).years());
    }

    @Test
    void theG194FlockReachesTheFarReedbed() {
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        CraneSpread m = CraneSpread.fromCohorts(flock, 1.0, 0.25, 100, 300);
        assertEquals(flock.lambda(), m.settings().lambda(), 0);
        Report r = m.run();
        int year = r.yearReached(40);
        assertTrue(year > 0, "never reached");
        // The front can never outrun c*: 40 km takes at least 40 / c* years.
        assertTrue(year >= 40 / m.spreadingSpeed());
        CraneSpread drought = CraneSpread.fromCohorts(
                CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT.withAdultSurvival(0.8), 1), 1.0, 0.25, 100, 300);
        assertEquals(-1, drought.run().yearReached(40));
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 1, 0.25, 100, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1.5, -1, 0.25, 100, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1.5, 1, 5, 100, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1.5, 1, 0.25, 100, 0));
        assertThrows(IllegalArgumentException.class, () -> CraneSpread.marsh(null, 1));
        assertThrows(IllegalArgumentException.class, () -> CraneSpread.fromCohorts(null, 1, 0.25, 100, 10));
    }
}
