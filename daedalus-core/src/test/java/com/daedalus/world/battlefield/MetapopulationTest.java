// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.Metapopulation.Outcome;
import com.daedalus.world.battlefield.Metapopulation.Report;
import com.daedalus.world.battlefield.Metapopulation.Settings;
import com.daedalus.world.battlefield.Metapopulation.Year;
import org.junit.jupiter.api.Test;

class MetapopulationTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 100;

    private static Report run(long seed, int plough) {
        Metapopulation m = Metapopulation.valley(D, seed);
        assertTrue(m.plough(0, plough));
        return m.run();
    }

    private static double lateMean(int plough) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += run(seed, plough).lateMean();
        }
        return sum / SEEDS;
    }

    @Test
    void levinsEquilibriumAndThresholdMatchTheTextbook() {
        Metapopulation m = Metapopulation.valley(D, 1);
        assertEquals(0.8, m.ploughThreshold(), 1e-12);
        assertEquals(0.4, m.equilibrium(0.4), 1e-12);
        assertEquals(0.0, m.equilibrium(0.9), 0.0);
        assertEquals(0.0, Metapopulation.valley(new Settings(100, 0, 0.1, 10, 10), 1).ploughThreshold(), 0.0);
    }

    @Test
    void longRunOccupancyTracksOneMinusDMinusEOverC() {
        Metapopulation m = Metapopulation.valley(D, 1);
        for (int plough : new int[] {0, 20, 40, 60}) {
            double expected = m.equilibrium(plough / (double) D.patches());
            double got = lateMean(plough);
            assertEquals(expected, got, 0.05, "ploughed " + plough);
        }
    }

    @Test
    void ploughingPastTheThresholdLosesTheButterfliesWhileMeadowsRemain() {
        for (int plough : new int[] {80, 90}) {
            int lost = 0;
            for (long seed = 1; seed <= SEEDS; seed++) {
                Report r = run(seed, plough);
                if (r.outcome() == Outcome.LOST) {
                    lost++;
                }
                assertEquals(plough, r.years().get(0).ploughed());
            }
            assertTrue(lost >= 95, plough + " ploughed, lost " + lost);
        }
        assertEquals(0, countLost(0));
        assertEquals(0, countLost(20));
    }

    private static int countLost(int plough) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            if (run(seed, plough).outcome() == Outcome.LOST) {
                n++;
            }
        }
        return n;
    }

    @Test
    void theExtinctionDebtIsPaidSlowly() {
        int alive10 = 0;
        int alive20 = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Report r = run(seed, 85);
            assertEquals(Outcome.LOST, r.outcome());
            if (r.years().get(10).occupied() > 0) {
                alive10++;
            }
            if (r.years().get(20).occupied() > 0) {
                alive20++;
            }
        }
        assertTrue(alive10 >= 90, "still flying in year 10: " + alive10);
        assertTrue(alive20 >= 70, "still flying in year 20: " + alive20);
    }

    @Test
    void lessPloughingMeansMoreButterflies() {
        double last = 2;
        for (int plough : new int[] {0, 20, 40, 60, 80}) {
            double m = lateMean(plough);
            assertTrue(m <= last, plough + " ploughed: " + m);
            last = m;
        }
    }

    @Test
    void ploughedPatchesStayEmpty() {
        for (long seed = 1; seed <= 20; seed++) {
            Metapopulation m = Metapopulation.valley(D, seed);
            assertTrue(m.plough(0, 30));
            assertTrue(m.plough(50, 20));
            for (Year y : m.run().years()) {
                assertTrue(y.occupied() <= D.patches() - y.ploughed());
                assertEquals(y.index() < 50 ? 30 : 50, y.ploughed());
            }
        }
    }

    @Test
    void flourishingMeadowsStayMeadow() {
        for (int plough : new int[] {0, 40, 85}) {
            for (long seed = 1; seed <= 10; seed++) {
                Report r = run(seed, plough);
                assertEquals(r.outcome() == Outcome.FLOURISHING ? Vegetation.MEADOW : Vegetation.SCRUB, r.band());
            }
        }
        assertEquals(Outcome.FLOURISHING, run(1, 0).outcome());
    }

    @Test
    void sameSeedSamePlanSameValley() {
        for (long seed = 1; seed <= 10; seed++) {
            assertEquals(run(seed, 40), run(seed, 40));
        }
    }

    @Test
    void badPlansAndSettingsAreRefused() {
        Metapopulation m = Metapopulation.valley(D, 1);
        assertFalse(m.plough(-1, 1));
        assertFalse(m.plough(D.years(), 1));
        assertFalse(m.plough(0, D.patches() + 1));
        assertTrue(m.plough(0, 60));
        assertFalse(m.plough(1, 41));
        assertThrows(IllegalArgumentException.class, () -> Metapopulation.valley(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 0.5, 0.1, 10, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(100, 0.5, 0, 10, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(100, 0.5, 0.1, 10, 101));
    }
}
