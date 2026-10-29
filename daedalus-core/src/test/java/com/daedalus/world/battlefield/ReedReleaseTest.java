// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.ReedRelease.Plan;
import com.daedalus.world.battlefield.ReedRelease.Settings;
import java.util.List;
import org.junit.jupiter.api.Test;

class ReedReleaseTest {

    private static final Settings D = Settings.DEFAULT;
    private static final ReedRelease P = ReedRelease.of(D, 7);
    private static final Plan BEST = P.best();

    @Test
    void bestIsTheBruteForceMinimum() {
        double min = Double.POSITIVE_INFINITY;
        int cap = D.perYear();
        for (double h : D.reedOptions()) {
            for (int a = 0; a <= cap; a++) {
                for (int b = 0; b <= cap; b++) {
                    for (int c = 0; c <= cap; c++) {
                        int d = D.budget() - a - b - c;
                        if (d < 0 || d > cap) {
                            continue;
                        }
                        min = Math.min(min, P.risk(h, new int[] {a, b, c, d}));
                    }
                }
            }
        }
        assertEquals(min, BEST.risk(), 0);
        assertEquals(D.budget(), BEST.schedule().stream().mapToInt(Integer::intValue).sum());
        assertEquals(BEST.risk(), P.risk(BEST.hectares(), BEST.schedule().stream().mapToInt(i -> i).toArray()), 0);
    }

    @Test
    void greedyIsNeverBetterAndClose() {
        Plan fast = P.fast();
        assertTrue(fast.risk() >= BEST.risk());
        assertTrue(fast.risk() - BEST.risk() <= 0.03, fast + " vs " + BEST);
    }

    @Test
    void bestReedSitsBelowTheHopfPoint() {
        double hopf = ReedCeiling.of(D.marsh()).cycleHectares();
        assertTrue(BEST.hectares() < hopf);
        double worstBelow = 0;
        double bestAbove = 1;
        for (double h : D.reedOptions()) {
            double r = P.bestSchedule(h).risk();
            if (h < hopf) {
                worstBelow = Math.max(worstBelow, r);
            } else {
                bestAbove = Math.min(bestAbove, r);
            }
        }
        assertTrue(bestAbove >= worstBelow, worstBelow + " vs " + bestAbove);
        assertEquals(1.0, bestAbove, 0.02);
    }

    @Test
    void moreReedNeverLowersTheRisk() {
        double prev = -1;
        for (double h : D.reedOptions()) {
            double r = P.bestSchedule(h).risk();
            assertTrue(r >= prev - 0.02, h + " " + r);
            prev = r;
        }
    }

    @Test
    void releasesHelpOnAModestReedbed() {
        assertTrue(P.bestSchedule(25).risk() < P.risk(25, new int[4]));
        ReedRelease none = ReedRelease.of(D.withBudget(0), 7);
        assertTrue(none.bestSchedule(25).risk() >= P.bestSchedule(25).risk());
    }

    @Test
    void seededPlansReplay() {
        Settings s = D.withReed(List.of(25.0, 55.0));
        assertEquals(ReedRelease.of(s, 3).best(), ReedRelease.of(s, 3).best());
    }

    @Test
    void badInputIsRejected() {
        ReedCeiling.Settings m = ReedCeiling.Settings.DEFAULT;
        assertThrows(IllegalArgumentException.class,
            () -> new Settings(m, List.of(), 6, 3, 8, 4, 4, 40, 4, 0.15, 10));
        assertThrows(IllegalArgumentException.class,
            () -> new Settings(m, List.of(10.0), 6, 3, 20, 4, 4, 40, 4, 0.15, 10));
        assertThrows(IllegalArgumentException.class,
            () -> new Settings(m, List.of(-1.0), 6, 3, 8, 4, 4, 40, 4, 0.15, 10));
        assertThrows(IllegalArgumentException.class,
            () -> new Settings(null, List.of(10.0), 6, 3, 8, 4, 4, 40, 4, 0.15, 10));
        assertThrows(IllegalArgumentException.class, () -> ReedRelease.of(null, 1));
        assertThrows(IllegalArgumentException.class, () -> P.risk(25, new int[] {1, 2}));
        assertThrows(IllegalArgumentException.class, () -> P.risk(25, new int[] {5, 3, 0, 0}));
    }
}
