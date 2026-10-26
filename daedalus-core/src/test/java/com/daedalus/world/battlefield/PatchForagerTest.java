// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.PatchForager.Outcome;
import com.daedalus.world.battlefield.PatchForager.Report;
import com.daedalus.world.battlefield.PatchForager.Settings;
import com.daedalus.world.battlefield.PatchForager.Visit;
import org.junit.jupiter.api.Test;

class PatchForagerTest {

    private static final Settings D = Settings.DEFAULT;

    @Test
    void charnovsRateHoardsTheWinter() {
        for (long seed = 1; seed <= 10; seed++) {
            PatchForager m = PatchForager.meadow(D, seed);
            Report r = m.rate(m.optimalRate());
            assertEquals(Outcome.HOARDED, r.outcome());
            assertEquals(1.0, r.share(), 1e-12);
        }
    }

    @Test
    void tooGreedyOrTooPatientFallsShort() {
        for (long seed = 1; seed <= 10; seed++) {
            PatchForager m = PatchForager.meadow(D, seed);
            double best = m.optimalRate();
            assertNotEquals(Outcome.HOARDED, m.rate(best * 0.25).outcome());
            assertNotEquals(Outcome.HOARDED, m.rate(best * 2).outcome());
            assertEquals(Outcome.STARVED, m.rate(best * 4).outcome());
            for (double f : new double[] {0.25, 0.5, 1.5, 2, 4}) {
                assertTrue(m.rate(best * f).berries() <= m.rate(best).berries(), "seed " + seed + " x" + f);
            }
        }
    }

    @Test
    void noFixedStayMatchesTheRateRuleOnUnevenPatches() {
        for (long seed = 1; seed <= 20; seed++) {
            PatchForager m = PatchForager.meadow(D, seed);
            double rateDay = m.rate(m.optimalRate()).berries();
            for (double minutes = 0.5; minutes <= 60; minutes += 0.5) {
                Report f = m.fixed(minutes);
                assertTrue(f.berries() < rateDay, seed + " / " + minutes + " min");
                assertNotEquals(Outcome.HOARDED, f.outcome(), seed + " / " + minutes + " min");
            }
        }
    }

    @Test
    void optimalRateIsCharnovsFixedPoint() {
        PatchForager m = PatchForager.meadow(D, 1);
        double theta = m.optimalRate();
        int bins = 200;
        double gain = 0;
        double time = 0;
        for (int b = 0; b < bins; b++) {
            double a = D.amount() * (1 + D.spread() * (2 * (b + 0.5) / bins - 1));
            double t = m.stay(a, theta);
            gain += a * (1 - Math.exp(-t / D.tau()));
            time += t;
        }
        assertEquals(theta, (gain / bins) / (time / bins + D.travel()), 1e-9);
        assertTrue(theta > 0 && theta < D.amount() / D.tau());
    }

    @Test
    void leavingRateEqualsTheThreshold() {
        PatchForager m = PatchForager.meadow(D, 2);
        double theta = m.optimalRate();
        for (double a : new double[] {60, 120, 220}) {
            double t = m.stay(a, theta);
            assertEquals(theta, a / D.tau() * Math.exp(-t / D.tau()), 1e-9);
        }
        assertEquals(0.0, m.stay(10, theta), 0.0);
    }

    @Test
    void theDayEndsAtDusk() {
        PatchForager m = PatchForager.meadow(D, 3);
        for (Report r : new Report[] {m.rate(m.optimalRate()), m.fixed(30), m.fixed(0)}) {
            double picking = 0;
            for (Visit v : r.visits()) {
                assertTrue(v.minutes() >= 0 && v.berries() >= 0);
                picking += v.minutes();
            }
            assertTrue(picking <= D.day() + 1e-9);
        }
        assertEquals(0.0, m.fixed(0).berries(), 0.0);
    }

    @Test
    void patchAmountsStayInTheirSpread() {
        PatchForager m = PatchForager.meadow(D, 4);
        for (int i = 0; i < D.patches(); i++) {
            assertTrue(m.held(i) >= D.amount() * (1 - D.spread()) && m.held(i) <= D.amount() * (1 + D.spread()));
        }
    }

    @Test
    void bandsShowWhatWasStripped() {
        PatchForager m = PatchForager.meadow(D, 5);
        Report r = m.rate(m.optimalRate() / 4);
        Visit first = r.visits().get(0);
        assertEquals(first.berries() > m.held(first.patch()) / 2 ? Vegetation.SCRUB : Vegetation.MEADOW,
                r.band(first.patch(), m.held(first.patch())));
        assertEquals(Vegetation.SCRUB, r.band(first.patch(), m.held(first.patch())));
        assertEquals(Vegetation.MEADOW, m.fixed(0).band(0, m.held(0)));
    }

    @Test
    void sameMeadowSameDay() {
        assertEquals(PatchForager.meadow(D, 9).rate(3.0), PatchForager.meadow(D, 9).rate(3.0));
        assertNotEquals(PatchForager.meadow(D, 9).held(0), PatchForager.meadow(D, 10).held(0));
    }

    @Test
    void badInputIsRefused() {
        PatchForager m = PatchForager.meadow(D, 1);
        assertThrows(IllegalArgumentException.class, () -> m.rate(0));
        assertThrows(IllegalArgumentException.class, () -> m.rate(Double.NaN));
        assertThrows(IllegalArgumentException.class, () -> m.fixed(-1));
        assertThrows(IllegalArgumentException.class, () -> PatchForager.meadow(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(120, 1200, 120, 1.0, 12, 8, 0.5, 0.97));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 1200, 120, 0.9, 12, 8, 0.5, 0.97));
    }
}
