// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class LucasLatticeTest {

    private static final int[] PRIMES = {2, 3, 5, 7, 11, 13, 97, 1_000_003};

    @Test
    void residuesMatchPascalTriangle() {
        int rows = 300;
        BigInteger[] row = {BigInteger.ONE};
        for (int n = 0; n <= rows; n++) {
            for (int k = 0; k <= n + 2; k++) {
                BigInteger c = k <= n ? row[k] : BigInteger.ZERO;
                for (int p : PRIMES) {
                    long want = c.mod(BigInteger.valueOf(p)).longValue();
                    assertThat(LucasLattice.binomialMod(n, k, p)).as("C(%d,%d) mod %d", n, k, p).isEqualTo(want);
                    if (k <= n) {
                        int e = 0;
                        BigInteger x = c;
                        BigInteger bp = BigInteger.valueOf(p);
                        while (x.mod(bp).signum() == 0) {
                            x = x.divide(bp);
                            e++;
                        }
                        assertThat(LucasLattice.primeExponent(n, k, p)).isEqualTo(e);
                    }
                }
            }
            BigInteger[] next = new BigInteger[n + 2];
            next[0] = BigInteger.ONE;
            next[n + 1] = BigInteger.ONE;
            for (int k = 1; k <= n; k++) {
                next[k] = row[k - 1].add(row[k]);
            }
            row = next;
        }
    }

    @Test
    void hugeRowsAgreeWithIdentities() {
        long n = LucasLattice.MAX_N;
        assertThat(LucasLattice.binomialMod(n, 0, 7)).isEqualTo(1);
        assertThat(LucasLattice.binomialMod(n, n, 1_000_003)).isEqualTo(1);
        assertThat(LucasLattice.binomialMod(n, 1, 1_000_003)).isEqualTo(n % 1_000_003);
        long m = (1L << 59) - 1;
        Random r = new Random(436);
        for (int t = 0; t < 200; t++) {
            long k = r.nextLong() & m;
            assertThat(LucasLattice.binomialMod(m, k, 2)).isEqualTo(1);
            assertThat(LucasLattice.primeExponent(m, k, 2)).isZero();
            long a = r.nextLong() & (m >> 1);
            long b = r.nextLong() & (m >> 1);
            assertThat(LucasLattice.binomialMod(a, b, 2)).isEqualTo((b & ~a) == 0 ? 1 : 0);
            assertThat(LucasLattice.primeExponent(a + b, b, 2))
                .isEqualTo(Long.bitCount(a) + Long.bitCount(b) - Long.bitCount(a + b));
        }
        assertThat(LucasLattice.primeExponent(10, 11, 3)).isEqualTo(-1);
    }

    @Test
    void gradesAndLines() {
        assertThat(LucasLattice.grade(10, 3, 7, 1)).isEqualTo(LucasLattice.Grade.TURNED);
        assertThat(LucasLattice.grade(10, 3, 7, 2)).isEqualTo(LucasLattice.Grade.SLIPPED);
        for (LucasLattice.Grade g : LucasLattice.Grade.values()) {
            assertThat(LucasLattice.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(LucasLattice.QUEST_ID).isEqualTo("q_lucas_lattice");
    }
}
