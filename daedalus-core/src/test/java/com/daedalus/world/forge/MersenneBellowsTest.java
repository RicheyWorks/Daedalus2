// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.Set;
import org.junit.jupiter.api.Test;

class MersenneBellowsTest {

    private static final Set<Integer> KNOWN = Set.of(2, 3, 5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521, 607, 1279,
        2203, 2281);

    @Test
    void lucasLehmerMatchesKnownExponentsAndProbablePrime() {
        for (int p = 2; p <= 2300; p++) {
            assertThat(MersenneBellows.isMersennePrime(p)).as("p=%d", p).isEqualTo(KNOWN.contains(p));
            if (p <= 700 && MersenneBellows.isPrimeInt(p)) {
                BigInteger m = BigInteger.ONE.shiftLeft(p).subtract(BigInteger.ONE);
                assertThat(MersenneBellows.lucasLehmer(p)).isEqualTo(m.isProbablePrime(40));
            }
        }
        assertThat(MersenneBellows.lucasLehmer(4423)).isTrue();
        assertThat(MersenneBellows.lucasLehmer(4421)).isFalse();
    }

    @Test
    void smallestFactorMatchesBruteForce() {
        for (int p = 3; p <= 61; p++) {
            if (!MersenneBellows.isPrimeInt(p)) {
                continue;
            }
            long m = (1L << p) - 1;
            long brute = 0;
            for (long f = 3; f <= 2_000_000 && f * f <= m; f += 2) {
                if (m % f == 0) {
                    brute = f;
                    break;
                }
            }
            long got = MersenneBellows.smallestFactor(p, 2_000_000 / (2L * p));
            assertThat(got).as("p=%d", p).isEqualTo(brute);
        }
        assertThat(MersenneBellows.smallestFactor(11, 10)).isEqualTo(23);
        assertThat(MersenneBellows.smallestFactor(67, 2_000_000)).isEqualTo(193_707_721L);
        assertThat(MersenneBellows.smallestFactor(4421, 1000)).isZero();
    }

    @Test
    void gradesAndLines() {
        assertThat(MersenneBellows.grade(31, true)).isEqualTo(MersenneBellows.Grade.TURNED);
        assertThat(MersenneBellows.grade(11, true)).isEqualTo(MersenneBellows.Grade.SLIPPED);
        assertThat(MersenneBellows.grade(9, false)).isEqualTo(MersenneBellows.Grade.TURNED);
        for (MersenneBellows.Grade g : MersenneBellows.Grade.values()) {
            assertThat(MersenneBellows.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(MersenneBellows.QUEST_ID).isEqualTo("q_mersenne_bellows");
    }
}
