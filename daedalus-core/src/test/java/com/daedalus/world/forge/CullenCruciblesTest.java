// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import org.junit.jupiter.api.Test;

class CullenCruciblesTest {

    private static BigInteger big(int n, int sign) {
        return BigInteger.valueOf(n).shiftLeft(n).add(BigInteger.valueOf(sign));
    }

    @Test
    void valuesAndPrimalityMatchBigInteger() {
        for (int n = 1; n <= CullenCrucibles.MAX_N; n++) {
            assertThat(CullenCrucibles.cullen(n)).isEqualTo(big(n, 1).longValueExact());
            assertThat(CullenCrucibles.woodall(n)).isEqualTo(big(n, -1).longValueExact());
            assertThat(CullenCrucibles.isPrimePour(CullenCrucibles.Kind.CULLEN, n)).as("C%d", n)
                    .isEqualTo(big(n, 1).isProbablePrime(60));
            assertThat(CullenCrucibles.isPrimePour(CullenCrucibles.Kind.WOODALL, n)).as("W%d", n)
                    .isEqualTo(big(n, -1).isProbablePrime(60));
        }
        assertThat(big(CullenCrucibles.MAX_N + 1, 1).bitLength()).isGreaterThan(63);
    }

    @Test
    void knownPrimePours() {
        assertThat(CullenCrucibles.primePours(CullenCrucibles.Kind.CULLEN, CullenCrucibles.MAX_N)).containsExactly(1);
        assertThat(CullenCrucibles.primePours(CullenCrucibles.Kind.WOODALL, CullenCrucibles.MAX_N))
                .containsExactly(2, 3, 6, 30);
        assertThat(CullenCrucibles.cullen(1)).isEqualTo(3);
        assertThat(CullenCrucibles.woodall(2)).isEqualTo(7);
        assertThat(CullenCrucibles.woodall(3)).isEqualTo(23);
        assertThat(CullenCrucibles.woodall(6)).isEqualTo(383);
    }

    @Test
    void smallestFactorsAreSound() {
        for (CullenCrucibles.Kind k : CullenCrucibles.Kind.values()) {
            for (int n = 1; n <= CullenCrucibles.MAX_N; n++) {
                long v = CullenCrucibles.pour(k, n);
                long f = CullenCrucibles.smallestFactor(k, n);
                if (v == 1) {
                    assertThat(f).isEqualTo(1);
                } else if (f == v) {
                    assertThat(CullenCrucibles.isPrimePour(k, n)).isTrue();
                } else if (f > 0) {
                    assertThat(v % f).isZero();
                    for (long d = 2; d < f; d++) {
                        assertThat(v % d).as("%s %d d=%d", k, n, d).isNotZero();
                    }
                } else {
                    assertThat(CullenCrucibles.isPrimePour(k, n)).isFalse();
                    for (long d = 2; d <= 20_000; d++) {
                        assertThat(v % d).isNotZero();
                    }
                }
            }
        }
        assertThat(CullenCrucibles.smallestFactor(CullenCrucibles.Kind.CULLEN, 2)).isEqualTo(3);
        assertThat(CullenCrucibles.smallestFactor(CullenCrucibles.Kind.WOODALL, 4)).isEqualTo(3);
    }

    @Test
    void edgesAndGuards() {
        assertThat(CullenCrucibles.woodall(1)).isEqualTo(1);
        assertThat(CullenCrucibles.smallestFactor(CullenCrucibles.Kind.WOODALL, 1)).isEqualTo(1);
        assertThat(CullenCrucibles.isPrimePour(CullenCrucibles.Kind.WOODALL, 1)).isFalse();
        assertThat(CullenCrucibles.cullen(CullenCrucibles.MAX_N)).isPositive();
        assertThat(CullenCrucibles.primePours(CullenCrucibles.Kind.CULLEN, 0)).isEmpty();
        assertThatThrownBy(() -> CullenCrucibles.cullen(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CullenCrucibles.woodall(CullenCrucibles.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CullenCrucibles.primePours(CullenCrucibles.Kind.CULLEN, -1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(CullenCrucibles.grade(CullenCrucibles.Kind.WOODALL, 30, true))
                .isEqualTo(CullenCrucibles.Grade.TURNED);
        assertThat(CullenCrucibles.grade(CullenCrucibles.Kind.CULLEN, 2, true))
                .isEqualTo(CullenCrucibles.Grade.SLIPPED);
        assertThat(CullenCrucibles.grade(CullenCrucibles.Kind.CULLEN, 2, false))
                .isEqualTo(CullenCrucibles.Grade.TURNED);
        for (CullenCrucibles.Grade g : CullenCrucibles.Grade.values()) {
            assertThat(CullenCrucibles.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(CullenCrucibles.QUEST_ID).isEqualTo("q_cullen_crucibles");
    }
}
