// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class PrimorialPyresTest {

    private static boolean trial(long n) {
        if (n < 2) {
            return false;
        }
        for (long d = 2; d * d <= n; d++) {
            if (n % d == 0) {
                return false;
            }
        }
        return true;
    }

    @Test
    void millerRabinMatchesTrialDivision() {
        for (long n = -5; n <= 300_000; n++) {
            assertThat(PrimorialPyres.isPrime(n)).as("n=%d", n).isEqualTo(trial(n));
        }
        Random r = new Random(498);
        for (int t = 0; t < 300; t++) {
            long n = (long) (r.nextDouble() * 1e12);
            assertThat(PrimorialPyres.isPrime(n)).as("n=%d", n).isEqualTo(trial(n));
        }
        for (int t = 0; t < 100; t++) {
            BigInteger p = BigInteger.probablePrime(31, r);
            BigInteger q = BigInteger.probablePrime(31, r);
            assertThat(PrimorialPyres.isPrime(p.longValueExact())).isTrue();
            assertThat(PrimorialPyres.isPrime(p.multiply(q).longValueExact())).isFalse();
            BigInteger big = BigInteger.probablePrime(62, r);
            assertThat(PrimorialPyres.isPrime(big.longValueExact())).isTrue();
        }
    }

    @Test
    void primorialsMatchPrimeProducts() {
        BigInteger want = BigInteger.ONE;
        for (int n = 0; n <= PrimorialPyres.MAX_N; n++) {
            if (trial(n)) {
                want = want.multiply(BigInteger.valueOf(n));
            }
            assertThat(PrimorialPyres.primorial(n)).as("%d#", n).isEqualTo(want.longValueExact());
        }
        assertThat(PrimorialPyres.primorial(13)).isEqualTo(30_030);
        assertThat(PrimorialPyres.primorial(47)).isEqualTo(614_889_782_588_491_410L);
    }

    @Test
    void knownFlames() {
        assertThat(PrimorialPyres.euclidFlames(PrimorialPyres.MAX_N)).containsExactly(2, 3, 5, 7, 11, 31);
        assertThat(PrimorialPyres.kummerFlames(PrimorialPyres.MAX_N)).containsExactly(3, 5, 11, 13, 41);
        assertThat(PrimorialPyres.isPrime(30_031)).isFalse();
        assertThat(59L * 509).isEqualTo(30_031);
        for (int p = 2; p <= PrimorialPyres.MAX_N; p++) {
            long e = PrimorialPyres.primorial(p) + 1;
            for (int q = 2; q <= p; q++) {
                if (trial(q)) {
                    assertThat(e % q).isEqualTo(1);
                }
            }
        }
    }

    @Test
    void edgesAndGuards() {
        assertThat(PrimorialPyres.primorial(0)).isEqualTo(1);
        assertThat(PrimorialPyres.primorial(1)).isEqualTo(1);
        assertThat(PrimorialPyres.isPrime(Long.MAX_VALUE)).isFalse();
        assertThat(PrimorialPyres.isPrime(9_223_372_036_854_775_783L)).isTrue();
        assertThat(PrimorialPyres.isPrime(3_215_031_751L)).isFalse();
        assertThat(PrimorialPyres.euclidFlames(1)).isEmpty();
        assertThatThrownBy(() -> PrimorialPyres.primorial(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PrimorialPyres.primorial(PrimorialPyres.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PrimorialPyres.kummerFlames(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(PrimorialPyres.grade(11, true)).isEqualTo(PrimorialPyres.Grade.TURNED);
        assertThat(PrimorialPyres.grade(13, true)).isEqualTo(PrimorialPyres.Grade.SLIPPED);
        assertThat(PrimorialPyres.grade(13, false)).isEqualTo(PrimorialPyres.Grade.TURNED);
        for (PrimorialPyres.Grade g : PrimorialPyres.Grade.values()) {
            assertThat(PrimorialPyres.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PrimorialPyres.QUEST_ID).isEqualTo("q_primorial_pyres");
    }
}
