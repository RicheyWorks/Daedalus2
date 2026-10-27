// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class AutomorphAnvilTest {

    @Test
    void checksMatchBruteForce() {
        List<Long> found = new ArrayList<>();
        for (long n = 0; n <= 1_000_000; n++) {
            long m = 1;
            while (m <= n) {
                m *= 10;
            }
            boolean want = n * n % m == n;
            assertThat(AutomorphAnvil.isAutomorphic(n, 10)).isEqualTo(want);
            if (want) {
                found.add(n);
            }
        }
        assertThat(found).containsExactly(0L, 1L, 5L, 6L, 25L, 76L, 376L, 625L, 9376L, 90625L, 109376L, 890625L);
        for (int b = 2; b <= 16; b++) {
            for (long n = 0; n <= 3000; n++) {
                long m = 1;
                long x = n;
                do {
                    m *= b;
                    x /= b;
                } while (x > 0);
                assertThat(AutomorphAnvil.isAutomorphic(n, b)).isEqualTo(n * n % m == n);
            }
        }
    }

    @Test
    void tailsAreIdempotents() {
        for (int k = 1; k <= 400; k++) {
            BigInteger mod = BigInteger.TEN.pow(k);
            BigInteger[] t = AutomorphAnvil.tails(k);
            for (BigInteger e : t) {
                assertThat(e.multiply(e).mod(mod)).isEqualTo(e);
            }
            assertThat(t[0].add(t[1])).isEqualTo(mod.add(BigInteger.ONE));
            assertThat(t[0].mod(BigInteger.valueOf(5).pow(k))).isZero();
            assertThat(t[1].mod(BigInteger.TWO.pow(k))).isZero();
            BigInteger next = AutomorphAnvil.tails(k + 1)[0];
            assertThat(next.mod(mod)).isEqualTo(t[0]);
        }
        assertThat(AutomorphAnvil.tails(4)[0]).isEqualTo(BigInteger.valueOf(625));
        assertThat(AutomorphAnvil.tails(4)[1]).isEqualTo(BigInteger.valueOf(9376));
        BigInteger[] big = AutomorphAnvil.tails(AutomorphAnvil.MAX_DIGITS);
        BigInteger mod = BigInteger.TEN.pow(AutomorphAnvil.MAX_DIGITS);
        assertThat(big[0].multiply(big[0]).mod(mod)).isEqualTo(big[0]);
    }

    @Test
    void gradesAndLines() {
        assertThat(AutomorphAnvil.grade(3, BigInteger.valueOf(376))).isEqualTo(AutomorphAnvil.Grade.TURNED);
        assertThat(AutomorphAnvil.grade(3, BigInteger.valueOf(375))).isEqualTo(AutomorphAnvil.Grade.SLIPPED);
        assertThat(AutomorphAnvil.grade(3, BigInteger.valueOf(1376))).isEqualTo(AutomorphAnvil.Grade.SLIPPED);
        for (AutomorphAnvil.Grade g : AutomorphAnvil.Grade.values()) {
            assertThat(AutomorphAnvil.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(AutomorphAnvil.QUEST_ID).isEqualTo("q_automorph_anvil");
    }
}
