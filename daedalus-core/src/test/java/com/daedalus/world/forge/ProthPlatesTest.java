// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Random;
import org.junit.jupiter.api.Test;

class ProthPlatesTest {

    private static final int LIM = 200_000;

    private static boolean[] bruteProth() {
        boolean[] p = new boolean[LIM + 1];
        for (int n = 1; (1L << n) + 1 <= LIM; n++) {
            for (long k = 1; k < (1L << n); k += 2) {
                long v = (k << n) + 1;
                if (v > LIM) {
                    break;
                }
                p[(int) v] = true;
            }
        }
        return p;
    }

    private static boolean trialPrime(long v) {
        if (v < 2) {
            return false;
        }
        for (long d = 2; d * d <= v; d++) {
            if (v % d == 0) {
                return false;
            }
        }
        return true;
    }

    @Test
    void structureMatchesEnumeration() {
        boolean[] p = bruteProth();
        long c = 0;
        for (int v = 1; v <= LIM; v++) {
            if (p[v]) {
                c++;
            }
            assertThat(ProthPlates.isProth(v)).as("%d", v).isEqualTo(p[v]);
            if (v % 997 == 0 || v < 300) {
                assertThat(ProthPlates.countProth(v)).as("count %d", v).isEqualTo(c);
            }
        }
        assertThat(ProthPlates.countProth(LIM)).isEqualTo(c);
    }

    @Test
    void prothTestMatchesTrialAndMillerRabin() {
        for (int v = 1; v <= LIM; v++) {
            if (ProthPlates.isProth(v)) {
                assertThat(ProthPlates.isProthPrime(v)).as("%d", v).isEqualTo(trialPrime(v));
            } else {
                assertThat(ProthPlates.isProthPrime(v)).isFalse();
            }
        }
        Random r = new Random(500);
        int seen = 0;
        for (int t = 0; t < 4000; t++) {
            int n = 1 + r.nextInt(29);
            long k = (r.nextLong() >>> 1) % (1L << n) | 1L;
            long v = (k << n) + 1;
            if (v > ProthPlates.MAX_N || (k >> n) != 0) {
                continue;
            }
            seen++;
            assertThat(ProthPlates.isProth(v)).isTrue();
            assertThat(ProthPlates.isProthPrime(v)).as("%d", v).isEqualTo(PrimorialPyres.isPrime(v));
        }
        assertThat(seen).isGreaterThan(3000);
    }

    @Test
    void knownPlatesAndPrimes() {
        long[] plates = {3, 5, 9, 13, 17, 25, 33, 41, 49, 57, 65, 81, 97, 113, 129, 145, 161, 177, 193, 209};
        StringBuilder got = new StringBuilder();
        StringBuilder want = new StringBuilder();
        int seen = 0;
        for (long v = 1; seen < plates.length; v++) {
            if (ProthPlates.isProth(v)) {
                got.append(v).append(',');
                want.append(plates[seen]).append(',');
                seen++;
            }
        }
        assertThat(got.toString()).isEqualTo(want.toString());
        for (long v : new long[] {3, 5, 13, 17, 41, 97, 113, 193, 241, 257, 353, 449, 577, 641, 673, 769, 929, 1153}) {
            assertThat(ProthPlates.isProthPrime(v)).as("%d", v).isTrue();
        }
        assertThat(ProthPlates.isProthPrime((1L << 32) + 1)).isFalse();
        assertThat(ProthPlates.isProthPrime(65_537)).isTrue();
        assertThat(ProthPlates.isProthPrime(3L * (1L << 30) + 1)).isEqualTo(PrimorialPyres.isPrime(3L * (1L << 30) + 1));
        assertThat(ProthPlates.split(97)).containsExactly(3, 5);
        assertThat(ProthPlates.witness(13)).isEqualTo(2);
        assertThat(ProthPlates.jacobi(2, 15)).isEqualTo(1);
        assertThat(ProthPlates.jacobi(5, 15)).isZero();
        assertThat(ProthPlates.jacobi(2, 13)).isEqualTo(-1);
    }

    @Test
    void edgesAndGuards() {
        assertThat(ProthPlates.isProth(1)).isFalse();
        assertThat(ProthPlates.isProth(2)).isFalse();
        assertThat(ProthPlates.isProth(7)).isFalse();
        assertThat(ProthPlates.countProth(0)).isZero();
        assertThat(ProthPlates.countProth(2)).isZero();
        assertThat(ProthPlates.countProth(3)).isEqualTo(1);
        assertThat(ProthPlates.countProth(ProthPlates.MAX_N)).isPositive();
        assertThat(ProthPlates.isProth(ProthPlates.MAX_N)).isFalse();
        long big = (1L << 59) + 1;
        assertThat(ProthPlates.isProth(big)).isTrue();
        assertThat(ProthPlates.isProthPrime(big)).isEqualTo(PrimorialPyres.isPrime(big));
        assertThatThrownBy(() -> ProthPlates.isProth(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ProthPlates.isProth(ProthPlates.MAX_N + 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ProthPlates.split(8)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ProthPlates.jacobi(3, 8)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ProthPlates.witness(10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ProthPlates.countProth(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(ProthPlates.grade(97, true)).isEqualTo(ProthPlates.Grade.TURNED);
        assertThat(ProthPlates.grade(25, true)).isEqualTo(ProthPlates.Grade.SLIPPED);
        assertThat(ProthPlates.grade(25, false)).isEqualTo(ProthPlates.Grade.TURNED);
        for (ProthPlates.Grade g : ProthPlates.Grade.values()) {
            assertThat(ProthPlates.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(ProthPlates.QUEST_ID).isEqualTo("q_proth_plates");
    }
}
