// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SailCutsTest {

    /** Brute force ray cast: is (x, y) (doubles) strictly inside the polygon. */
    private static boolean inside(long[][] p, double x, double y) {
        boolean in = false;
        for (int i = 0, j = p.length - 1; i < p.length; j = i++) {
            if ((p[i][1] > y) != (p[j][1] > y)
                && x < (double) (p[j][0] - p[i][0]) * (y - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]) {
                in = !in;
            }
        }
        return in;
    }

    /** Star-shaped sail: distinct angles around the origin with random radii. */
    private static long[][] star(SplittableRandom r, int n) {
        long[][] p = new long[n][];
        for (int i = 0; i < n; i++) {
            double ang = 2 * Math.PI * (i + 0.1 + 0.8 * r.nextDouble()) / n;
            double rad = 50 + r.nextInt(950);
            p[i] = new long[] {Math.round(rad * Math.cos(ang)), Math.round(rad * Math.sin(ang))};
        }
        return p;
    }

    private static boolean simple(long[][] p) {
        try {
            SailCuts.cut(p);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    private static void verify(long[][] p, int[][] tr) {
        int n = p.length;
        assertThat(tr.length).isEqualTo(n - 2);
        assertThat(SailCuts.totalDoubledArea(p, tr)).isEqualTo(Math.abs(SailCuts.doubledArea(p)));
        for (int[] t : tr) {
            assertThat(SailCuts.cross(p[t[0]], p[t[1]], p[t[2]])).isPositive();
            double cx = (p[t[0]][0] + p[t[1]][0] + p[t[2]][0]) / 3.0;
            double cy = (p[t[0]][1] + p[t[1]][1] + p[t[2]][1]) / 3.0;
            assertThat(inside(p, cx, cy)).isTrue();
            for (int e = 0; e < 3; e++) {
                int a = t[e];
                int b = t[(e + 1) % 3];
                if ((a + 1) % n == b || (b + 1) % n == a) {
                    continue;
                }
                for (int i = 0; i < n; i++) {
                    int j = (i + 1) % n;
                    if (i == a || i == b || j == a || j == b) {
                        continue;
                    }
                    assertThat(SailCuts.meet(p[a], p[b], p[i], p[j])).isFalse();
                }
            }
        }
    }

    @Test
    void squareAndClockwiseSquare() {
        long[][] sq = {{0, 0}, {4, 0}, {4, 4}, {0, 4}};
        verify(sq, SailCuts.cut(sq));
        long[][] cw = {{0, 0}, {0, 4}, {4, 4}, {4, 0}};
        verify(cw, SailCuts.cut(cw));
        assertThat(SailCuts.quest(sq, 2, 32)).isTrue();
        assertThat(SailCuts.quest(sq, 2, 31)).isFalse();
    }

    @Test
    void combWithTeethMatchesBruteForce() {
        int teeth = 12;
        long[][] p = new long[2 * teeth + 2][];
        int k = 0;
        for (int i = 0; i < teeth; i++) {
            p[k++] = new long[] {2L * i, 10};
            p[k++] = new long[] {2L * i + 1, 1};
        }
        p[k++] = new long[] {2L * teeth, 0};
        p[k] = new long[] {-1, 0};
        long[][] cw = new long[p.length][];
        for (int i = 0; i < p.length; i++) {
            cw[i] = p[p.length - 1 - i];
        }
        verify(cw, SailCuts.cut(cw));
        verify(p, SailCuts.cut(p));
    }

    @Test
    void randomStarSailsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(446);
        int done = 0;
        for (int it = 0; it < 300; it++) {
            long[][] p = star(r, 3 + r.nextInt(40));
            if (!simple(p)) {
                continue;
            }
            verify(p, SailCuts.cut(p));
            done++;
        }
        assertThat(done).isGreaterThan(200);
    }

    @Test
    void largestSailCuts() {
        long[][] p = star(new SplittableRandom(7), SailCuts.MAX_CORNERS);
        if (simple(p)) {
            verify(p, SailCuts.cut(p));
        }
        long[][] ring = new long[SailCuts.MAX_CORNERS][];
        for (int i = 0; i < ring.length; i++) {
            ring[i] = new long[] {i, (long) i * i};
        }
        assertThat(SailCuts.cut(ring).length).isEqualTo(ring.length - 2);
    }

    @Test
    void rejectsBadSails() {
        assertThatThrownBy(() -> SailCuts.cut(new long[][] {{0, 0}, {1, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SailCuts.cut(new long[][] {{0, 0}, {2, 2}, {2, 0}, {0, 2}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SailCuts.cut(new long[][] {{0, 0}, {1, 1}, {2, 2}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SailCuts.cut(new long[][] {{0, 0}, {1, 0}, {0, 0}, {0, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SailCuts.cut(new long[][] {{0, 0}, {5_000_000, 0}, {0, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}