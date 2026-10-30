// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RootQuenchTest {

    private static boolean prime(int n) {
        return n >= 2 && BigInteger.valueOf(n).isProbablePrime(40);
    }

    @Test
    void matchesBruteForceForSmallPrimes() {
        for (int p = 2; p < 2000; p++) {
            if (!prime(p)) {
                continue;
            }
            long[] root = new long[p];
            java.util.Arrays.fill(root, -1);
            for (long t = p - 1; t >= 0; t--) {
                root[(int) (t * t % p)] = t;
            }
            for (int a = 0; a < p; a++) {
                assertThat(RootQuench.sqrtMod(a, p)).isEqualTo(root[a]);
                if (p > 2) {
                    long euler = BigInteger.valueOf(a).modPow(BigInteger.valueOf((p - 1) / 2), BigInteger.valueOf(p))
                        .longValue();
                    int want = a == 0 ? 0 : euler == 1 ? 1 : -1;
                    assertThat(RootQuench.jacobi(a, p)).isEqualTo(want);
                }
            }
        }
    }

    @Test
    void jacobiMultiplicativeAndLargePrimes() {
        for (int n = 3; n < 400; n += 2) {
            for (int a = -50; a < 50; a++) {
                int prod = 1;
                int m = n;
                for (int q = 3; q <= m; q += 2) {
                    while (m % q == 0) {
                        prod *= RootQuench.jacobi(a, q);
                        m /= q;
                    }
                }
                assertThat(RootQuench.jacobi(a, n)).isEqualTo(prod);
            }
        }
        SplittableRandom r = new SplittableRandom(426);
        for (int t = 0; t < 40; t++) {
            long p = BigInteger.valueOf(r.nextLong(1L << 61) + (1L << 40)).nextProbablePrime().longValue();
            long x = r.nextLong(p);
            long a = BigInteger.valueOf(x).multiply(BigInteger.valueOf(x)).mod(BigInteger.valueOf(p)).longValue();
            long s = RootQuench.sqrtMod(a, p);
            assertThat(s == x || s == p - x).isTrue();
            assertThat(RootQuench.jacobi(a, p)).isIn(0, 1);
        }
        assertThat(RootQuench.sqrtMod(10, 13)).isEqualTo(6);
        assertThat(RootQuench.sqrtMod(5, 13)).isEqualTo(-1);
        assertThat(RootQuench.jacobi(1001, 9907)).isEqualTo(-1);
        assertThat(RootQuench.jacobi(19, 45)).isEqualTo(1);
    }

    @Test
    void grades() {
        assertThat(RootQuench.grade(10, 13, 7)).isEqualTo(RootQuench.Grade.QUENCHED);
        assertThat(RootQuench.grade(10, 13, 5)).isEqualTo(RootQuench.Grade.CRACKED);
        assertThat(RootQuench.grade(5, 13, -1)).isEqualTo(RootQuench.Grade.QUENCHED);
        assertThat(RootQuench.forgemasterLine(RootQuench.Grade.QUENCHED)).contains("Forgemaster");
        assertThat(RootQuench.forgemasterLine(RootQuench.Grade.CRACKED)).contains("cracked");
        assertThat(RootQuench.QUEST_ID).isEqualTo("q_root_quench");
    }
}
