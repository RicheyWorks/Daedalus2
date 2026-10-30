// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class FermatFoldTest {

    @Test
    void matchesBruteNearestDivisor() {
        for (long n = 1; n <= 30_001; n += 2) {
            long a = FermatFold.isqrt(n);
            while (n % a != 0) {
                a--;
            }
            long b = n / a;
            long[] f = FermatFold.fold(n, FermatFold.MAX_STEPS);
            assertThat(f).as("n=%d", n).hasSize(3);
            assertThat(f[0]).isEqualTo(a);
            assertThat(f[1]).isEqualTo(b);
            long s = FermatFold.isqrt(n);
            long x0 = s * s == n ? s : s + 1;
            assertThat(f[2]).isEqualTo((a + b) / 2 - x0);
        }
    }

    @Test
    void closePrimePairsAtScale() {
        Random r = new Random(445);
        for (int t = 0; t < 40; t++) {
            BigInteger p = BigInteger.valueOf(900_000_000L + r.nextInt(90_000_000)).nextProbablePrime();
            BigInteger q = p.add(BigInteger.valueOf(2 + r.nextInt(100_000))).nextProbablePrime();
            long n = p.multiply(q).longValueExact();
            long[] f = FermatFold.fold(n, FermatFold.MAX_STEPS);
            assertThat(f).hasSize(3);
            assertThat(f[0]).isEqualTo(p.longValue());
            assertThat(f[1]).isEqualTo(q.longValue());
        }
        assertThat(FermatFold.fold(3L * 333_333_333_333_333_331L, 10)).isEmpty();
        assertThat(FermatFold.fold(1, 0)).containsExactly(1, 1, 0);
    }

    @Test
    void gradesAndLines() {
        assertThat(FermatFold.grade(5959, 59, 101)).isEqualTo(FermatFold.Grade.TURNED);
        assertThat(FermatFold.grade(5959, 1, 5959)).isEqualTo(FermatFold.Grade.SLIPPED);
        for (FermatFold.Grade g : FermatFold.Grade.values()) {
            assertThat(FermatFold.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(FermatFold.QUEST_ID).isEqualTo("q_fermat_fold");
    }
}
