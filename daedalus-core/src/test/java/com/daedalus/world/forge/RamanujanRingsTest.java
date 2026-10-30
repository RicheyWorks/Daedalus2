// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class RamanujanRingsTest {

    @Test
    void sumsMatchCosineBruteForce() {
        for (int q = 1; q <= 150; q++) {
            for (int n = -5; n <= 160; n++) {
                double s = 0;
                for (int a = 1; a <= q; a++) {
                    if (RamanujanRings.gcd(a, q) == 1) {
                        s += Math.cos(2 * Math.PI * a * (double) n / q);
                    }
                }
                assertThat(RamanujanRings.ramanujanSum(q, n)).as("c_%d(%d)", q, n).isEqualTo(Math.round(s));
            }
        }
    }

    @Test
    void arithmeticFunctionsMatchBruteForce() {
        for (int q = 1; q <= 400; q++) {
            long phi = 0;
            long j2 = 0;
            for (int a = 1; a <= q; a++) {
                if (RamanujanRings.gcd(a, q) == 1) {
                    phi++;
                }
                for (int b = 1; b <= q; b++) {
                    if (RamanujanRings.gcd(RamanujanRings.gcd(a, b), q) == 1) {
                        j2++;
                    }
                }
            }
            assertThat(RamanujanRings.totient(q)).isEqualTo(phi);
            assertThat(RamanujanRings.jordanTotient(1, q)).isEqualTo(phi);
            assertThat(RamanujanRings.jordanTotient(2, q)).isEqualTo(j2);
            long psi = 0;
            for (int d = 1; d <= q; d++) {
                if (q % d == 0) {
                    long m = q / d;
                    boolean sf = true;
                    for (long p = 2; p * p <= m; p++) {
                        if (m % (p * p) == 0) {
                            sf = false;
                        }
                    }
                    if (sf) {
                        psi += d;
                    }
                }
            }
            assertThat(RamanujanRings.dedekindPsi(q)).as("psi(%d)", q).isEqualTo(psi);
            long sumMu = 0;
            for (int d = 1; d <= q; d++) {
                if (q % d == 0) {
                    sumMu += RamanujanRings.mobius(d);
                }
            }
            assertThat(sumMu).isEqualTo(q == 1 ? 1 : 0);
        }
        long big = RamanujanRings.MAX_Q;
        assertThat(RamanujanRings.totient(big)).isEqualTo(big / 10 * 4);
        assertThat(RamanujanRings.dedekindPsi(big)).isEqualTo(big / 10 * 18);
        assertThat(RamanujanRings.ramanujanSum(big, 0)).isEqualTo(RamanujanRings.totient(big));
        assertThat(RamanujanRings.ramanujanSum(999_999_999_989L, 1)).isEqualTo(-1);
    }

    @Test
    void gradesAndLines() {
        assertThat(RamanujanRings.grade(12, 2, 2)).isEqualTo(RamanujanRings.Grade.TURNED);
        assertThat(RamanujanRings.grade(12, 2, 0)).isEqualTo(RamanujanRings.Grade.SLIPPED);
        for (RamanujanRings.Grade g : RamanujanRings.Grade.values()) {
            assertThat(RamanujanRings.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(RamanujanRings.QUEST_ID).isEqualTo("q_ramanujan_rings");
    }
}
