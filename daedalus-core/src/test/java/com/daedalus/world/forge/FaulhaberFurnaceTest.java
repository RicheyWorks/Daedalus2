// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class FaulhaberFurnaceTest {

    private static BigInteger brute(int k, long n) {
        BigInteger s = BigInteger.ZERO;
        for (long i = 1; i <= n; i++) {
            s = s.add(BigInteger.valueOf(i).pow(k));
        }
        return s;
    }

    private static String b(int m) {
        BigInteger[] q = FaulhaberFurnace.bernoulli(m);
        return q[0] + "/" + q[1];
    }

    @Test
    void bernoulliMatchesKnownValues() {
        String[] want = {"1/1", "1/2", "1/6", "0/1", "-1/30", "0/1", "1/42", "0/1", "-1/30", "0/1", "5/66", "0/1",
            "-691/2730", "0/1", "7/6"};
        for (int m = 0; m < want.length; m++) {
            assertThat(b(m)).as("B%d", m).isEqualTo(want[m]);
        }
        for (int m = 3; m <= FaulhaberFurnace.MAX_K; m += 2) {
            assertThat(b(m)).isEqualTo("0/1");
        }
        assertThat(FaulhaberFurnace.bernoulli(60)[1]).isEqualTo(BigInteger.valueOf(56786730L));
    }

    @Test
    void powerSumsMatchBruteForce() {
        for (int k = 0; k <= 12; k++) {
            for (long n = 0; n <= 120; n++) {
                assertThat(FaulhaberFurnace.powerSum(k, n)).as("k=%d n=%d", k, n).isEqualTo(brute(k, n));
            }
        }
        Random r = new Random(431);
        for (int t = 0; t < 60; t++) {
            int k = r.nextInt(FaulhaberFurnace.MAX_K + 1);
            long n = r.nextInt(400);
            assertThat(FaulhaberFurnace.powerSum(k, n)).isEqualTo(brute(k, n));
        }
        BigInteger n = BigInteger.valueOf(1_000_000_000_000L);
        BigInteger tri = n.multiply(n.add(BigInteger.ONE)).shiftRight(1);
        assertThat(FaulhaberFurnace.powerSum(1, 1_000_000_000_000L)).isEqualTo(tri);
        assertThat(FaulhaberFurnace.powerSum(3, 1_000_000_000_000L)).isEqualTo(tri.multiply(tri));
        assertThat(FaulhaberFurnace.powerSum(0, Long.MAX_VALUE)).isEqualTo(BigInteger.valueOf(Long.MAX_VALUE));
        BigInteger[][] c = FaulhaberFurnace.coefficients(2);
        assertThat(c[3]).containsExactly(BigInteger.ONE, BigInteger.valueOf(3));
        assertThat(c[2]).containsExactly(BigInteger.ONE, BigInteger.valueOf(2));
        assertThat(c[1]).containsExactly(BigInteger.ONE, BigInteger.valueOf(6));
    }

    @Test
    void gradesAndLines() {
        assertThat(FaulhaberFurnace.grade(2, 10, BigInteger.valueOf(385))).isEqualTo(FaulhaberFurnace.Grade.TURNED);
        assertThat(FaulhaberFurnace.grade(2, 10, BigInteger.valueOf(384))).isEqualTo(FaulhaberFurnace.Grade.SLIPPED);
        for (FaulhaberFurnace.Grade g : FaulhaberFurnace.Grade.values()) {
            assertThat(FaulhaberFurnace.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(FaulhaberFurnace.QUEST_ID).isEqualTo("q_faulhaber_furnace");
    }
}
