// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Random;
import org.junit.jupiter.api.Test;

class GaussianGearsTest {

    private static long bruteMaxCommonNorm(long a, long b, long c, long d) {
        long lim = Math.max(Math.max(Math.abs(a), Math.abs(b)), Math.max(Math.abs(c), Math.abs(d)));
        long best = 0;
        for (long x = -lim; x <= lim; x++) {
            for (long y = -lim; y <= lim; y++) {
                if ((x != 0 || y != 0) && GaussianGears.divides(x, y, a, b) && GaussianGears.divides(x, y, c, d)) {
                    best = Math.max(best, x * x + y * y);
                }
            }
        }
        return best;
    }

    private static boolean brutePrime(long a, long b) {
        long n = a * a + b * b;
        if (n < 2) {
            return false;
        }
        long lim = (long) Math.sqrt((double) n) + 1;
        for (long x = -lim; x <= lim; x++) {
            for (long y = -lim; y <= lim; y++) {
                long m = x * x + y * y;
                if (m > 1 && m < n && GaussianGears.divides(x, y, a, b)) {
                    return false;
                }
            }
        }
        return true;
    }

    @Test
    void gcdAndPrimesMatchBruteForce() {
        Random r = new Random(428);
        for (int t = 0; t < 400; t++) {
            long a = r.nextInt(25) - 12;
            long b = r.nextInt(25) - 12;
            long c = r.nextInt(25) - 12;
            long d = r.nextInt(25) - 12;
            long[] g = GaussianGears.gcd(a, b, c, d);
            if (a == 0 && b == 0 && c == 0 && d == 0) {
                assertThat(g).containsExactly(0, 0);
                continue;
            }
            assertThat(GaussianGears.divides(g[0], g[1], a, b)).isTrue();
            assertThat(GaussianGears.divides(g[0], g[1], c, d)).isTrue();
            assertThat(g[0] * g[0] + g[1] * g[1]).isEqualTo(bruteMaxCommonNorm(a, b, c, d));
            assertThat(g[0] > 0 && g[1] >= 0).isTrue();
        }
        for (long a = -20; a <= 20; a++) {
            for (long b = -20; b <= 20; b++) {
                assertThat(GaussianGears.isPrime(a, b)).as("%d+%di", a, b).isEqualTo(brutePrime(a, b));
            }
        }
        long big = GaussianGears.MAX_PART;
        assertThat(GaussianGears.gcd(big, big - 1, big - 1, big)).isNotNull();
    }

    @Test
    void twoSquaresMatchBruteCounts() {
        int lim = 5000;
        long[] cnt = new long[lim + 1];
        for (long x = -71; x <= 71; x++) {
            for (long y = -71; y <= 71; y++) {
                long m = x * x + y * y;
                if (m <= lim) {
                    cnt[(int) m]++;
                }
            }
        }
        for (int n = 0; n <= lim; n++) {
            assertThat(GaussianGears.countRepresentations(n)).as("r2(%d)", n).isEqualTo(cnt[n]);
            long[] s = GaussianGears.twoSquares(n);
            if (cnt[n] == 0) {
                assertThat(s).isEmpty();
            } else {
                assertThat(s[0] * s[0] + s[1] * s[1]).isEqualTo(n);
                assertThat(s[0] >= s[1] && s[1] >= 0).isTrue();
            }
        }
        Random r = new Random(4280);
        for (int t = 0; t < 300; t++) {
            long n = (long) (r.nextDouble() * GaussianGears.MAX_N);
            long[] s = GaussianGears.twoSquares(n);
            assertThat(s.length == 0).isEqualTo(GaussianGears.countRepresentations(n) == 0);
            if (s.length > 0) {
                assertThat(s[0] * s[0] + s[1] * s[1]).isEqualTo(n);
            }
        }
        long[] s = GaussianGears.twoSquares(GaussianGears.MAX_N);
        assertThat(s[0] * s[0] + s[1] * s[1]).isEqualTo(GaussianGears.MAX_N);
        assertThat(GaussianGears.twoSquares(999_999_999_999L)).isEmpty();
    }

    @Test
    void gradesAndLines() {
        assertThat(GaussianGears.grade(25, 4, 3)).isEqualTo(GaussianGears.Grade.TURNED);
        assertThat(GaussianGears.grade(25, 4, 2)).isEqualTo(GaussianGears.Grade.SLIPPED);
        assertThat(GaussianGears.grade(2, Long.MAX_VALUE, 1)).isEqualTo(GaussianGears.Grade.SLIPPED);
        for (GaussianGears.Grade g : GaussianGears.Grade.values()) {
            assertThat(GaussianGears.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(GaussianGears.QUEST_ID).isEqualTo("q_gaussian_gears");
    }
}
