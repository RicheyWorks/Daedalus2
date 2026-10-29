// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.LuckyFeather.Result;
import com.daedalus.world.battlefield.LuckyFeather.Settings;
import org.junit.jupiter.api.Test;

class LuckyFeatherTest {

    private static LuckyFeather aviary(int n, double r, int i) {
        return LuckyFeather.of(new Settings(n, r, i, 1_000_000));
    }

    /** Brute force: dense Gaussian elimination with partial pivoting on the full (N+1)x(N+1) chain. */
    private static double[] dense(LuckyFeather m, boolean steps) {
        int n = m.settings().flock();
        double[][] a = new double[n + 1][n + 2];
        a[0][0] = 1;
        a[n][n] = 1;
        a[n][n + 1] = steps ? 0 : 1;
        for (int i = 1; i < n; i++) {
            a[i][i] = m.up(i) + m.down(i);
            a[i][i + 1] = -m.up(i);
            a[i][i - 1] = -m.down(i);
            a[i][n + 1] = steps ? 1 : 0;
        }
        for (int col = 0; col <= n; col++) {
            int piv = col;
            for (int r = col + 1; r <= n; r++) {
                if (Math.abs(a[r][col]) > Math.abs(a[piv][col])) {
                    piv = r;
                }
            }
            double[] t = a[col];
            a[col] = a[piv];
            a[piv] = t;
            for (int r = 0; r <= n; r++) {
                if (r != col) {
                    double f = a[r][col] / a[col][col];
                    for (int c = col; c <= n + 1; c++) {
                        a[r][c] -= f * a[col][c];
                    }
                }
            }
        }
        double[] x = new double[n + 1];
        for (int i = 0; i <= n; i++) {
            x[i] = a[i][n + 1] / a[i][i];
        }
        return x;
    }

    @Test
    void neutralAlleleFixesInProportion() {
        for (int n : new int[] {2, 5, 20, 100}) {
            LuckyFeather m = aviary(n, 1.0, 1);
            for (int i = 0; i <= n; i++) {
                assertEquals((double) i / n, m.fixation(i), 1e-12);
            }
        }
    }

    @Test
    void closedFormMatchesTheExactChain() {
        for (int n = 2; n <= 30; n++) {
            for (double r : new double[] {0.5, 0.9, 0.999999, 1.0, 1.1, 1.5, 3.0}) {
                LuckyFeather m = aviary(n, r, 1);
                double[] p = m.exact();
                for (int i = 0; i <= n; i++) {
                    assertEquals(m.fixation(i), p[i], 1e-10, "N " + n + " r " + r + " i " + i);
                }
            }
        }
    }

    @Test
    void thomasMatchesDenseGaussianBruteForce() {
        for (int n : new int[] {3, 10, 25}) {
            for (double r : new double[] {0.7, 1.0, 2.0}) {
                LuckyFeather m = aviary(n, r, 1);
                double[] p = dense(m, false);
                double[] t = dense(m, true);
                double[] pe = m.exact();
                double[] te = m.meanStepsAll();
                for (int i = 0; i <= n; i++) {
                    assertEquals(p[i], pe[i], 1e-10);
                    assertEquals(t[i], te[i], 1e-7 * Math.max(1, t[i]));
                }
            }
        }
    }

    @Test
    void seededSimulationMatchesFixationOdds() {
        for (double r : new double[] {1.0, 1.5}) {
            LuckyFeather m = aviary(20, r, 2);
            int runs = 4000;
            Result res = m.simulate(runs, 9);
            double p = m.fixation();
            double sd = Math.sqrt(p * (1 - p) / runs);
            assertEquals(p, res.fixed(), 4 * sd, "r " + r);
            assertEquals(0, res.capped());
            assertEquals(m.meanSteps(), res.meanSteps(), 0.06 * m.meanSteps());
        }
    }

    @Test
    void selectionTiltsTheOdds() {
        int n = 20;
        assertTrue(aviary(n, 1.2, 1).fixation() > 1.0 / n);
        assertTrue(aviary(n, 0.8, 1).fixation() < 1.0 / n);
        double prev = 0;
        for (double r = 0.5; r <= 3; r += 0.25) {
            double f = aviary(n, r, 1).fixation();
            assertTrue(f > prev);
            prev = f;
        }
    }

    @Test
    void bigFlocksApproachOneMinusOneOverR() {
        for (double r : new double[] {1.5, 2.0, 4.0}) {
            assertEquals(1 - 1 / r, aviary(5000, r, 1).fixation(), 1e-9);
        }
    }

    @Test
    void questCountsTheCarriersNeeded() {
        LuckyFeather m = LuckyFeather.of(Settings.aviary(1.1));
        assertEquals(20, m.settings().flock());
        for (double target : new double[] {0.1, 0.5, 0.9, 0.99}) {
            int k = m.carriersNeeded(target);
            assertTrue(m.fixation(k) >= target - 1e-12);
            assertTrue(k == 0 || m.fixation(k - 1) < target);
        }
        assertEquals(0, m.carriersNeeded(0));
        assertEquals(20, m.carriersNeeded(1));
    }

    @Test
    void seededRunsReplay() {
        LuckyFeather m = LuckyFeather.of(Settings.aviary(1.3).withStart(3));
        assertEquals(m.simulate(300, 5), m.simulate(300, 5));
        assertNotEquals(m.simulate(300, 5), m.simulate(300, 6));
    }

    @Test
    void stepCapIsReported() {
        Result res = LuckyFeather.of(new Settings(200, 1.0, 100, 5)).simulate(50, 1);
        assertEquals(50, res.capped());
        assertEquals(0, res.fixed(), 0);
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 1, 0, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(10, 0, 1, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(10, 1, 11, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(10, 1, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> LuckyFeather.of(null));
        LuckyFeather m = aviary(10, 1.2, 1);
        assertThrows(IllegalArgumentException.class, () -> m.fixation(11));
        assertThrows(IllegalArgumentException.class, () -> m.carriersNeeded(1.5));
        assertThrows(IllegalArgumentException.class, () -> m.simulate(0, 1));
    }
}
