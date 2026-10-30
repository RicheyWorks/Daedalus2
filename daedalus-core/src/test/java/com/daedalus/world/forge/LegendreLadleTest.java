// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import org.junit.jupiter.api.Test;

class LegendreLadleTest {

    private static final int[] PRIMES = {2, 3, 5, 7, 11, 13, 31, 97, 1_000_003};

    @Test
    void matchesExactFactorials() {
        BigInteger f = BigInteger.ONE;
        for (int n = 0; n <= 400; n++) {
            if (n > 0) {
                f = f.multiply(BigInteger.valueOf(n));
            }
            for (int p : PRIMES) {
                BigInteger bp = BigInteger.valueOf(p);
                BigInteger x = f;
                long v = 0;
                while (x.mod(bp).signum() == 0) {
                    x = x.divide(bp);
                    v++;
                }
                assertThat(LegendreLadle.valuation(n, p)).as("v_%d(%d!)", p, n).isEqualTo(v);
                assertThat(LegendreLadle.factorialUnitMod(n, p)).isEqualTo(x.mod(bp).longValue());
            }
            for (int b = 2; b <= 60; b++) {
                BigInteger bb = BigInteger.valueOf(b);
                BigInteger x = f;
                long z = 0;
                while (x.mod(bb).signum() == 0) {
                    x = x.divide(bb);
                    z++;
                }
                assertThat(LegendreLadle.trailingZeros(n, b)).as("n=%d b=%d", n, b).isEqualTo(z);
            }
        }
    }

    @Test
    void hugePoursAgreeWithIdentities() {
        long n = LegendreLadle.MAX_N;
        assertThat(LegendreLadle.valuation(n, 2)).isEqualTo(n - Long.bitCount(n));
        assertThat(LegendreLadle.trailingZeros(n, 10)).isEqualTo(LegendreLadle.valuation(n, 5));
        assertThat(LegendreLadle.trailingZeros(n, 16)).isEqualTo((n - Long.bitCount(n)) / 4);
        assertThat(LegendreLadle.factorialUnitMod(1_000_002, 1_000_003)).isEqualTo(1_000_002);
        assertThat(LegendreLadle.trailingZeros(100, 10)).isEqualTo(24);
    }

    @Test
    void gradesAndLines() {
        assertThat(LegendreLadle.grade(100, 10, 24)).isEqualTo(LegendreLadle.Grade.TURNED);
        assertThat(LegendreLadle.grade(100, 10, 20)).isEqualTo(LegendreLadle.Grade.SLIPPED);
        for (LegendreLadle.Grade g : LegendreLadle.Grade.values()) {
            assertThat(LegendreLadle.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(LegendreLadle.QUEST_ID).isEqualTo("q_legendre_ladle");
    }
}
