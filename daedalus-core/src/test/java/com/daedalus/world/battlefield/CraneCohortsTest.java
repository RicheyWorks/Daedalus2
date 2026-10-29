// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.CraneCohorts.Outcome;
import com.daedalus.world.battlefield.CraneCohorts.Report;
import com.daedalus.world.battlefield.CraneCohorts.Settings;
import java.util.List;
import org.junit.jupiter.api.Test;

class CraneCohortsTest {

    private static final Settings D = Settings.DEFAULT;

    /** Euler-Lotka residual for this matrix shape: Fs l2 / L^3 + Fa l3 / (L^4 (1 - p / L)) - 1. */
    private static double eulerLotka(Settings s, double l) {
        double l2 = s.chickSurvival() * s.juvenileSurvival();
        double l3 = l2 * s.subadultSurvival();
        return s.subadultFecundity() * l2 / Math.pow(l, 3)
                + s.adultFecundity() * l3 / (Math.pow(l, 4) * (1 - s.adultSurvival() / l)) - 1;
    }

    @Test
    void lambdaSolvesEulerLotka() {
        Settings[] all = {D, D.withAdultSurvival(0.8), new Settings(0.3, 0.6, 0.9, 0.95, 0.0, 0.6, 10),
            new Settings(0.9, 0.9, 0.9, 0.5, 1.2, 2.0, 10)};
        for (Settings s : all) {
            double l = CraneCohorts.marsh(s, 1).lambda();
            assertTrue(l > s.adultSurvival());
            assertEquals(0, eulerLotka(s, l), 1e-9, s.toString());
        }
        assertEquals(1.0290662633, CraneCohorts.marsh(D, 1).lambda(), 1e-8);
        assertEquals(0.9605619165, CraneCohorts.marsh(D.withAdultSurvival(0.8), 1).lambda(), 1e-8);
    }

    @Test
    void noChicksMeansLambdaIsAdultSurvival() {
        CraneCohorts c = CraneCohorts.marsh(new Settings(0.5, 0.7, 0.85, 0.9, 0, 0, 10), 1);
        assertEquals(0.9, c.lambda(), 1e-9);
        assertEquals(Outcome.DECLINING, c.trend());
    }

    @Test
    void eigenvectorsAreRightAndLeft() {
        CraneCohorts c = CraneCohorts.marsh(D, 1);
        List<Double> w = c.stableAges();
        List<Double> v = c.reproductiveValue();
        assertEquals(1.0, w.stream().mapToDouble(Double::doubleValue).sum(), 1e-12);
        assertEquals(1.0, v.get(CraneCohorts.CHICK), 1e-12);
        for (int i = 0; i < CraneCohorts.COHORTS; i++) {
            double aw = 0;
            double va = 0;
            for (int j = 0; j < CraneCohorts.COHORTS; j++) {
                aw += c.entry(i, j) * w.get(j);
                va += v.get(j) * c.entry(j, i);
            }
            assertEquals(c.lambda() * w.get(i), aw, 1e-10);
            assertEquals(c.lambda() * v.get(i), va, 1e-10);
            assertTrue(w.get(i) > 0 && v.get(i) > 0);
        }
        // Reproductive value climbs with age up to the breeding cohorts.
        assertTrue(v.get(1) > v.get(0) && v.get(2) > v.get(1));
    }

    @Test
    void elasticitiesSumToOneAndAdultSurvivalDominates() {
        CraneCohorts c = CraneCohorts.marsh(D, 1);
        double sum = 0;
        for (int i = 0; i < CraneCohorts.COHORTS; i++) {
            for (int j = 0; j < CraneCohorts.COHORTS; j++) {
                sum += c.elasticity(i, j);
            }
        }
        assertEquals(1.0, sum, 1e-10);
        double adult = c.elasticity(CraneCohorts.ADULT, CraneCohorts.ADULT);
        assertTrue(adult > c.elasticity(0, CraneCohorts.ADULT));
        assertTrue(adult > c.elasticity(1, 0));
        // Each juvenile-path survival carries the same elasticity (every life cycle through it passes them all).
        assertEquals(c.elasticity(1, 0), c.elasticity(2, 1), 1e-10);
    }

    @Test
    void deterministicFlockSettlesToStableAges() {
        CraneCohorts c = CraneCohorts.marsh(D, 1);
        double[] n = {0, 0, 0, 30};
        double prevTotal = 30;
        double ratio = 0;
        for (int t = 0; t < 300; t++) {
            n = c.step(n);
            double total = n[0] + n[1] + n[2] + n[3];
            ratio = total / prevTotal;
            prevTotal = total;
        }
        assertEquals(c.lambda(), ratio, 1e-9);
        for (int i = 0; i < CraneCohorts.COHORTS; i++) {
            assertEquals(c.stableAges().get(i), n[i] / prevTotal, 1e-9);
        }
    }

    @Test
    void bigNoisyFlocksGrowAtLambda() {
        Settings s = new Settings(0.5, 0.7, 0.85, 0.9, 0.15, 0.45, 20);
        CraneCohorts c = CraneCohorts.marsh(s, 1);
        int[] start = new int[CraneCohorts.COHORTS];
        for (int i = 0; i < CraneCohorts.COHORTS; i++) {
            start[i] = (int) Math.round(4000 * c.stableAges().get(i));
        }
        int startTotal = start[0] + start[1] + start[2] + start[3];
        double logSum = 0;
        int seeds = 10;
        for (long seed = 1; seed <= seeds; seed++) {
            logSum += Math.log((double) c.project(start, seed).flock() / startTotal) / s.years();
        }
        assertEquals(Math.log(c.lambda()), logSum / seeds, 0.005);
    }

    @Test
    void releasingBreedersBeatsReleasingChicks() {
        CraneCohorts c = CraneCohorts.marsh(D, 7);
        assertEquals(CraneCohorts.ADULT, c.bestRelease());
        int chicksLost = 0;
        int adultsLost = 0;
        for (long seed = 1; seed <= 200; seed++) {
            if (c.project(new int[] {6, 0, 0, 0}, seed).outcome() == Outcome.EXTINCT) {
                chicksLost++;
            }
            if (c.project(new int[] {0, 0, 0, 6}, seed).outcome() == Outcome.EXTINCT) {
                adultsLost++;
            }
        }
        assertTrue(chicksLost > adultsLost + 40, chicksLost + " vs " + adultsLost);
        // The Allee hook: six chicks are worth far fewer adults than six adults.
        assertTrue(c.adultEquivalents(new int[] {6, 0, 0, 0}) < 6);
        assertEquals(6, c.adultEquivalents(new int[] {0, 0, 0, 6}));
    }

    @Test
    void seededRunsReplay() {
        CraneCohorts c = CraneCohorts.marsh(D, 42);
        int[] start = {10, 8, 6, 20};
        Report a = c.project(start);
        Report b = CraneCohorts.marsh(D, 42).project(start);
        assertEquals(a, b);
        assertEquals(a, c.project(start, 42));
        assertNotEquals(a.years(), c.project(start, 43).years());
        assertEquals(start[3], a.years().get(0).adults());
        assertEquals(D.years() + 1, a.years().size());
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(1.2, 0.7, 0.85, 0.9, 0.1, 0.4, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.5, 0.7, 0.85, 0.9, -1, 0.4, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.5, 0.7, 0.85, 0.9, 0.1, 0.4, 0));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.5, 0.7, 0.85, 0, 0, 0, 10));
        assertThrows(IllegalArgumentException.class, () -> CraneCohorts.marsh(null, 1));
        CraneCohorts c = CraneCohorts.marsh(D, 1);
        assertThrows(IllegalArgumentException.class, () -> c.project(new int[] {1, 2, 3}));
        assertThrows(IllegalArgumentException.class, () -> c.project(new int[] {1, -2, 3, 4}));
    }
}
