// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class OwlFixTest {
    @Test
    void solverFindsTheOwlOnEverySeed() {
        for (long s = 0; s < 300; s++) {
            OwlFix f = OwlFix.seeded(s);
            assertEquals(f.owl(), f.solve(), "seed " + s);
            assertTrue(f.judge(f.solve()).exact());
            assertEquals(100, f.judge(f.solve()).score());
        }
    }

    @Test
    void solverEqualsIndependentArgminAndIsDeterministic() {
        for (long s = 0; s < 50; s++) {
            OwlFix f = OwlFix.seeded(s);
            OwlFix.Cell best = null;
            double b = Double.MAX_VALUE;
            for (int y = 0; y < OwlFix.GRID; y++) {
                for (int x = 0; x < OwlFix.GRID; x++) {
                    OwlFix.Cell c = new OwlFix.Cell(x, y);
                    double m = OwlFix.misfit(c, f.delays());
                    if (m < b) {
                        b = m;
                        best = c;
                    }
                }
            }
            assertEquals(best, f.solve());
            assertEquals(f.solve(), OwlFix.seeded(s).solve());
        }
    }

    @Test
    void nearestPostHearsFirst() {
        for (long s = 0; s < 200; s++) {
            OwlFix f = OwlFix.seeded(s);
            double[] d = f.delays();
            int near = 0;
            for (int i = 1; i < 4; i++) {
                if (OwlFix.travel(f.owl(), i) < OwlFix.travel(f.owl(), near)) {
                    near = i;
                }
            }
            double gap = Double.MAX_VALUE;
            for (int i = 0; i < 4; i++) {
                if (i != near) {
                    gap = Math.min(gap, OwlFix.travel(f.owl(), i) - OwlFix.travel(f.owl(), near));
                }
            }
            if (gap > 3 * OwlFix.JITTER_S) {
                for (int i = 0; i < 4; i++) {
                    assertTrue(i == near || d[i] > d[near], "seed " + s);
                }
            }
        }
    }

    @Test
    void delaysArePhysical() {
        double maxDiff = Math.hypot(500, 500) / OwlFix.SOUND_MPS + 2 * OwlFix.JITTER_S;
        for (long s = 0; s < 200; s++) {
            double[] d = OwlFix.seeded(s).delays();
            assertEquals(0.0, d[0]);
            for (double v : d) {
                assertTrue(Math.abs(v) <= maxDiff);
            }
        }
    }

    @Test
    void hootIsLowAndJudgeScalesWithDistance() {
        for (long s = 0; s < 200; s++) {
            double hz = OwlFix.seeded(s).hootHz();
            assertTrue(hz >= 250 && hz <= 350);
        }
        OwlFix f = OwlFix.seeded(7);
        OwlFix.Cell o = f.owl();
        OwlFix.Cell off = new OwlFix.Cell(o.x() == 0 ? 1 : o.x() - 1, o.y());
        assertFalse(f.judge(off).exact());
        assertEquals(80, f.judge(off).score());
        assertEquals(0, f.judge(new OwlFix.Cell(-1, 0)).score());
        assertEquals(0, f.judge(null).score());
    }

    @Test
    void trueCellResidualIsZeroWithNoiseOff() {
        for (OwlFix.Cell c : OwlFix.cells()) {
            assertEquals(0.0, OwlFix.misfit(c, OwlFix.exactDelays(c)), 1e-24);
        }
    }

    @Test
    void argminIsUniqueWithNoMirrorWithinTimingTolerance() {
        // Worst-case noise: each difference off by up to 2 jitters (+ 0.05 ms rounding); 3 differences.
        double e = 2 * OwlFix.JITTER_S + 0.00005;
        double tol = 3 * e * e;
        for (long s = 0; s < 300; s++) {
            OwlFix f = OwlFix.seeded(s);
            OwlFix.Cell best = f.solve();
            double far = Double.MAX_VALUE;
            int ties = 0;
            double bm = OwlFix.misfit(best, f.delays());
            for (OwlFix.Cell c : OwlFix.cells()) {
                double m = OwlFix.misfit(c, f.delays());
                if (m == bm) {
                    ties++;
                }
                if (Math.max(Math.abs(c.x() - best.x()), Math.abs(c.y() - best.y())) > 2) {
                    far = Math.min(far, m);
                }
            }
            assertEquals(1, ties, "seed " + s);
            assertTrue(far > 10 * tol, "seed " + s + " far " + far);
        }
    }
}