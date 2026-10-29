// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class RationSharesTest {

    @Test
    void greedySumsExactly() {
        for (long b = 2; b <= 70; b++) {
            for (long a = 1; a < b; a++) {
                List<BigInteger> g = RationShares.greedy(a, b);
                BigInteger num = BigInteger.ZERO;
                BigInteger den = BigInteger.ONE;
                for (int i = 0; i < g.size(); i++) {
                    if (i > 0) {
                        assertThat(g.get(i)).isGreaterThan(g.get(i - 1));
                    }
                    num = num.multiply(g.get(i)).add(den);
                    den = den.multiply(g.get(i));
                }
                assertThat(num.multiply(BigInteger.valueOf(b))).as("%d/%d", a, b).isEqualTo(den.multiply(BigInteger.valueOf(a)));
            }
        }
        assertThat(RationShares.greedy(4, 13)).containsExactly(BigInteger.valueOf(4), BigInteger.valueOf(18), BigInteger.valueOf(468));
    }

    private static int bruteFewest(long a, long b, int maxDen) {
        List<Long> dens = new ArrayList<>();
        for (long d = 2; d <= maxDen; d++) {
            dens.add(d);
        }
        for (int k = 1; k <= 3; k++) {
            if (choose(a, b, dens, 0, k, BigInteger.ZERO, BigInteger.ONE)) {
                return k;
            }
        }
        return 0;
    }

    private static boolean choose(long a, long b, List<Long> dens, int from, int k, BigInteger num, BigInteger den) {
        if (k == 0) {
            return num.multiply(BigInteger.valueOf(b)).equals(den.multiply(BigInteger.valueOf(a)));
        }
        for (int i = from; i < dens.size(); i++) {
            BigInteger d = BigInteger.valueOf(dens.get(i));
            if (choose(a, b, dens, i + 1, k - 1, num.multiply(d).add(den), den.multiply(d))) {
                return true;
            }
        }
        return false;
    }

    @Test
    void shortestMatchesBruteForce() {
        for (long b = 2; b <= 16; b++) {
            for (long a = 1; a < b; a++) {
                List<Long> s = RationShares.shortest(a, b, 3, 30);
                assertThat(s.size()).as("%d/%d", a, b).isEqualTo(bruteFewest(a, b, 30));
                if (!s.isEmpty()) {
                    assertThat(RationShares.quest(a, b, s)).isTrue();
                }
            }
        }
        assertThat(RationShares.shortest(4, 13, 3, 200)).hasSize(3);
    }

    @Test
    void questAndBounds() {
        assertThat(RationShares.quest(2, 3, List.of(2L, 6L))).isTrue();
        assertThat(RationShares.quest(2, 3, List.of(3L, 3L))).isFalse();
        assertThat(RationShares.quest(2, 3, List.of(2L, 7L))).isFalse();
        assertThat(RationShares.QUEST_ID).isEqualTo("q_ration_shares");
        assertThatThrownBy(() -> RationShares.greedy(3, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RationShares.shortest(1, 2, 0, 10)).isInstanceOf(IllegalArgumentException.class);
    }
}