// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class HarbourWardsTest {

    private static boolean inConvex(double[][] poly, double x, double y, double tol) {
        for (int i = 0; i < poly.length; i++) {
            double[] p = poly[i];
            double[] q = poly[(i + 1) % poly.length];
            double cr = (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0]);
            if (cr < -tol) {
                return false;
            }
        }
        return poly.length >= 3;
    }

    /** Brute force: index of the nearest site. */
    private static int nearest(long[][] s, double x, double y) {
        int best = 0;
        for (int i = 1; i < s.length; i++) {
            if (Math.hypot(s[i][0] - x, s[i][1] - y) < Math.hypot(s[best][0] - x, s[best][1] - y)) {
                best = i;
            }
        }
        return best;
    }

    private static long[][] randomSites(SplittableRandom r, int n, int span) {
        long[][] s = new long[n][];
        int k = 0;
        while (k < n) {
            long[] c = {r.nextInt(-span / 4, span + span / 4), r.nextInt(-span / 4, span + span / 4)};
            boolean dup = false;
            for (int j = 0; j < k; j++) {
                dup |= s[j][0] == c[0] && s[j][1] == c[1];
            }
            if (!dup) {
                s[k++] = c;
            }
        }
        return s;
    }

    @Test
    void twoByTwoGridSplitsEvenly() {
        long[][] s = {{1, 1}, {3, 1}, {1, 3}, {3, 3}};
        long[] box = {0, 0, 4, 4};
        for (int i = 0; i < 4; i++) {
            assertThat(HarbourWards.area(HarbourWards.cell(s, box, i))).isCloseTo(4.0, within(1e-9));
            assertThat(HarbourWards.quest(s, box, i, 4)).isTrue();
        }
        assertThat(HarbourWards.quest(s, box, 0, 5)).isFalse();
    }

    @Test
    void singleSiteOwnsWholeBox() {
        double[][] c = HarbourWards.cell(new long[][] {{50, 50}}, new long[] {0, 0, 10, 20}, 0);
        assertThat(HarbourWards.area(c)).isCloseTo(200.0, within(1e-9));
    }

    @Test
    void randomHarboursMatchNearestSiteBruteForce() {
        SplittableRandom r = new SplittableRandom(452);
        for (int it = 0; it < 60; it++) {
            int span = 20 + r.nextInt(1000);
            long[][] s = randomSites(r, 1 + r.nextInt(30), span);
            long[] box = {0, 0, span, span};
            double[][][] cells = new double[s.length][][];
            double total = 0;
            for (int i = 0; i < s.length; i++) {
                cells[i] = HarbourWards.cell(s, box, i);
                total += HarbourWards.area(cells[i]);
                assertThat(HarbourWards.area(cells[i])).isGreaterThanOrEqualTo(-1e-9);
            }
            assertThat(total).isCloseTo((double) span * span, within(1e-6 * span * span));
            for (int k = 0; k < 200; k++) {
                double x = r.nextDouble() * span;
                double y = r.nextDouble() * span;
                int w = nearest(s, x, y);
                assertThat(inConvex(cells[w], x, y, 1e-6 * span)).isTrue();
            }
        }
    }

    @Test
    void largestHarbourAreasSumToBox() {
        long[][] s = randomSites(new SplittableRandom(9), HarbourWards.MAX_SITES, 800_000);
        long[] box = {0, 0, 800_000, 800_000};
        double total = 0;
        for (int i = 0; i < s.length; i++) {
            total += HarbourWards.area(HarbourWards.cell(s, box, i));
        }
        assertThat(total).isCloseTo(6.4e11, within(1e3));
    }

    @Test
    void rejectsBadInput() {
        long[] box = {0, 0, 4, 4};
        assertThatThrownBy(() -> HarbourWards.cell(new long[0][], box, 0))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HarbourWards.cell(new long[][] {{1, 1}, {1, 1}}, box, 0))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HarbourWards.cell(new long[][] {{1, 1}}, new long[] {4, 0, 0, 4}, 0))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HarbourWards.cell(new long[][] {{1, 1}}, box, 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}