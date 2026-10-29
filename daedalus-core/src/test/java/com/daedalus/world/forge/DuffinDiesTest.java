// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class DuffinDiesTest {

    private static long bruteSigma(long n) {
        long s = 0;
        for (long d = 1; d <= n; d++) {
            if (n % d == 0) {
                s += d;
            }
        }
        return s;
    }

    private static boolean brute(long n) {
        long s = bruteSigma(n);
        boolean composite = n > 3 && s != n + 1;
        return composite && BigInteger.valueOf(n).gcd(BigInteger.valueOf(s)).equals(BigInteger.ONE);
    }

    @Test
    void matchesDivisorLoopBruteForce() {
        long run = 0;
        for (long n = 1; n <= 50_000; n++) {
            boolean b = brute(n);
            if (n <= 5000) {
                assertThat(DuffinDies.sigma(n)).isEqualTo(bruteSigma(n));
            }
            assertThat(DuffinDies.isDuffinian(n)).as("n=%d", n).isEqualTo(b);
            run += b ? 1 : 0;
            if (n % 997 == 0 || n < 80) {
                assertThat(DuffinDies.countDuffinian((int) n)).isEqualTo(run);
            }
        }
    }

    @Test
    void knownDuffinDiesAndRuns() {
        List<Long> first = new ArrayList<>();
        for (long n = 1; first.size() < 20; n++) {
            if (DuffinDies.isDuffinian(n)) {
                first.add(n);
            }
        }
        assertThat(first).containsExactly(4L, 8L, 9L, 16L, 21L, 25L, 27L, 32L, 35L, 36L, 39L, 49L, 50L, 55L, 57L,
                63L, 64L, 65L, 75L, 77L);
        assertThat(DuffinDies.firstRun(2, 1000)).isEqualTo(8);
        assertThat(DuffinDies.firstRun(3, 1000)).isEqualTo(63);
    }

    @Test
    void sieveAgreesWithChecksOnRandomWindows() {
        Random r = new Random(497);
        for (int t = 0; t < 5; t++) {
            int lo = 100_000 + r.nextInt(3_000_000);
            int hi = lo + r.nextInt(3000);
            long c = DuffinDies.countDuffinian(lo);
            for (long n = lo + 1; n <= hi; n++) {
                c += DuffinDies.isDuffinian(n) ? 1 : 0;
            }
            assertThat(DuffinDies.countDuffinian(hi)).isEqualTo(c);
        }
        for (int t = 0; t < 300; t++) {
            long n = 2 + (long) (r.nextDouble() * 1e11);
            long s = DuffinDies.sigma(n);
            assertThat(s).isGreaterThan(n);
            assertThat(DuffinDies.isDuffinian(n)).isEqualTo(
                    s != n + 1 && BigInteger.valueOf(n).gcd(BigInteger.valueOf(s)).equals(BigInteger.ONE));
        }
    }

    @Test
    void primesPrimePowersEdgesAndGuards() {
        long[] primes = {2, 3, 5, 7, 11, 13, 101, 999_983, 999_999_999_989L};
        for (long p : primes) {
            assertThat(DuffinDies.isDuffinian(p)).isFalse();
            long pk = p;
            while (pk <= DuffinDies.MAX_N / p) {
                pk *= p;
                assertThat(DuffinDies.isDuffinian(pk)).as("%d", pk).isTrue();
            }
        }
        assertThat(DuffinDies.isDuffinian(1)).isFalse();
        assertThat(DuffinDies.sigma(1)).isEqualTo(1);
        assertThat(DuffinDies.countDuffinian(0)).isZero();
        assertThat(DuffinDies.firstRun(4, 2000)).isGreaterThanOrEqualTo(-1);
        assertThatThrownBy(() -> DuffinDies.sigma(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DuffinDies.isDuffinian(DuffinDies.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DuffinDies.countDuffinian(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DuffinDies.firstRun(0, 10)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(DuffinDies.grade(21, true)).isEqualTo(DuffinDies.Grade.TURNED);
        assertThat(DuffinDies.grade(6, true)).isEqualTo(DuffinDies.Grade.SLIPPED);
        assertThat(DuffinDies.grade(7, false)).isEqualTo(DuffinDies.Grade.TURNED);
        for (DuffinDies.Grade g : DuffinDies.Grade.values()) {
            assertThat(DuffinDies.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(DuffinDies.QUEST_ID).isEqualTo("q_duffin_dies");
    }
}
