// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class DockCalipersTest {

    private static long bruteDiameter(long[][] p) {
        long best = 0;
        for (long[] a : p) {
            for (long[] b : p) {
                best = Math.max(best, DockCalipers.dist2(a, b));
            }
        }
        return best;
    }

    /** Brute width: over every pair direction with all buoys on one side, the farthest buoy. */
    private static double bruteWidth(long[][] p) {
        double best = Double.MAX_VALUE;
        boolean any = false;
        for (long[] a : p) {
            for (long[] b : p) {
                if (a[0] == b[0] && a[1] == b[1]) {
                    continue;
                }
                any = true;
                long lo = 0;
                long hi = 0;
                for (long[] q : p) {
                    long c = DockCalipers.cross(a, b, q);
                    lo = Math.min(lo, c);
                    hi = Math.max(hi, c);
                }
                if (lo == 0 || hi == 0) {
                    best = Math.min(best, (hi - lo) / Math.sqrt(DockCalipers.dist2(a, b)));
                }
            }
        }
        return any ? best : 0;
    }

    @Test
    void rectangleKnownAnswers() {
        long[][] p = {{0, 0}, {6, 0}, {6, 3}, {0, 3}, {2, 1}, {3, 0}};
        assertThat(DockCalipers.diameterSquared(p)).isEqualTo(45);
        assertThat(DockCalipers.width(p)).isCloseTo(3.0, within(1e-9));
        assertThat(DockCalipers.quest(p, 45)).isTrue();
        assertThat(DockCalipers.quest(p, 44)).isFalse();
    }

    @Test
    void randomFieldsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(461);
        for (int it = 0; it < 2000; it++) {
            int n = 1 + r.nextInt(12);
            int span = 1 + r.nextInt(it % 2 == 0 ? 5 : 1000);
            long[][] p = new long[n][];
            for (int i = 0; i < n; i++) {
                p[i] = new long[] {r.nextInt(-span, span + 1), r.nextInt(-span, span + 1)};
            }
            assertThat(DockCalipers.diameterSquared(p)).isEqualTo(bruteDiameter(p));
            assertThat(DockCalipers.width(p)).isCloseTo(bruteWidth(p), within(1e-6));
        }
    }

    @Test
    void collinearAndSingleBuoys() {
        assertThat(DockCalipers.diameterSquared(new long[][] {{5, 5}, {5, 5}})).isZero();
        long[][] line = {{0, 0}, {2, 2}, {4, 4}, {1, 1}};
        assertThat(DockCalipers.diameterSquared(line)).isEqualTo(32);
        assertThat(DockCalipers.width(line)).isZero();
    }

    @Test
    void largestFlatField() {
        int n = DockCalipers.MAX_BUOYS;
        long[][] p = new long[n][];
        SplittableRandom r = new SplittableRandom(7);
        for (int i = 0; i < n; i++) {
            p[i] = new long[] {r.nextInt(-1_000_000, 1_000_001), r.nextInt(-1_000, 1_001)};
        }
        p[0] = new long[] {-1_000_000, 0};
        p[1] = new long[] {1_000_000, 0};
        assertThat(DockCalipers.diameterSquared(p)).isGreaterThanOrEqualTo(4_000_000_000_000L);
        assertThat(DockCalipers.width(p)).isLessThanOrEqualTo(2_000.0);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> DockCalipers.hull(new long[0][]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DockCalipers.hull(new long[][] {{0, 2_000_000}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}