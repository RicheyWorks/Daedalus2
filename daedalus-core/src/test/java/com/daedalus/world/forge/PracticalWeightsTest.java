// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.BitSet;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class PracticalWeightsTest {

    private static long bruteGap(int n) {
        int sigma = 0;
        for (int d = 1; d <= n; d++) {
            if (n % d == 0) {
                sigma += d;
            }
        }
        BitSet reach = new BitSet(sigma + 2);
        reach.set(0);
        for (int d = n; d >= 1; d--) {
            if (n % d == 0) {
                for (int s = sigma - d; s >= 0; s--) {
                    if (reach.get(s)) {
                        reach.set(s + d);
                    }
                }
            }
        }
        return reach.nextClearBit(1);
    }

    @Test
    void matchesSubsetSumBruteForce() {
        long run = 0;
        for (int n = 1; n <= 3000; n++) {
            long gap = bruteGap(n);
            boolean want = gap >= n;
            assertThat(PracticalWeights.smallestUnweighable(n)).as("gap n=%d", n).isEqualTo(gap);
            assertThat(PracticalWeights.isPractical(n)).as("n=%d", n).isEqualTo(want);
            if (want) {
                run++;
            }
            if (n % 97 == 0 || n < 40) {
                assertThat(PracticalWeights.countPractical(n)).isEqualTo(run);
            }
        }
    }

    @Test
    void knownPracticalNumbers() {
        List<Long> first = new ArrayList<>();
        for (long n = 1; first.size() < 30; n++) {
            if (PracticalWeights.isPractical(n)) {
                first.add(n);
            }
        }
        assertThat(first).containsExactly(1L, 2L, 4L, 6L, 8L, 12L, 16L, 18L, 20L, 24L, 28L, 30L, 32L, 36L, 40L, 42L,
                48L, 54L, 56L, 60L, 64L, 66L, 72L, 78L, 80L, 84L, 88L, 90L, 96L, 100L);
        assertThat(PracticalWeights.countPractical(100)).isEqualTo(30);
        assertThat(PracticalWeights.divisors(12)).containsExactly(1L, 2L, 3L, 4L, 6L, 12L);
        assertThat(PracticalWeights.smallestUnweighable(10)).isEqualTo(4);
    }

    @Test
    void criterionAgreesWithGreedyOnRandomSweeps() {
        Random r = new Random(473);
        for (int t = 0; t < 400; t++) {
            long n = 2L * (1 + (long) (r.nextDouble() * 49_999_999L));
            assertThat(PracticalWeights.isPractical(n)).as("n=%d", n)
                    .isEqualTo(PracticalWeights.smallestUnweighable(n) >= n);
        }
        long f = 1;
        for (int k = 1; k <= 14; k++) {
            f *= k;
            assertThat(PracticalWeights.isPractical(f)).as("%d!", k).isTrue();
        }
        for (int k = 0; k <= 39; k++) {
            assertThat(PracticalWeights.isPractical(1L << k)).isTrue();
        }
        for (long odd = 3; odd < 2000; odd += 2) {
            assertThat(PracticalWeights.isPractical(odd)).isFalse();
            assertThat(PracticalWeights.smallestUnweighable(odd)).isEqualTo(2);
        }
    }

    @Test
    void edgesAndBigStamps() {
        assertThat(PracticalWeights.countPractical(0)).isZero();
        assertThat(PracticalWeights.countPractical(1)).isEqualTo(1);
        assertThat(PracticalWeights.isPractical(1)).isTrue();
        assertThat(PracticalWeights.smallestUnweighable(1)).isEqualTo(2);
        assertThat(PracticalWeights.isPractical(PracticalWeights.MAX_N)).isTrue();
        long semi = 2L * 499_999_999_979L;
        assertThat(PracticalWeights.isPractical(semi)).isFalse();
        assertThat(PracticalWeights.smallestUnweighable(semi)).isEqualTo(4);
        assertThatThrownBy(() -> PracticalWeights.isPractical(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PracticalWeights.isPractical(PracticalWeights.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PracticalWeights.countPractical(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PracticalWeights.countPractical(PracticalWeights.MAX_RACK + 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(PracticalWeights.grade(12, true)).isEqualTo(PracticalWeights.Grade.WEIGHED);
        assertThat(PracticalWeights.grade(10, true)).isEqualTo(PracticalWeights.Grade.SHORT);
        assertThat(PracticalWeights.grade(10, false)).isEqualTo(PracticalWeights.Grade.WEIGHED);
        for (PracticalWeights.Grade g : PracticalWeights.Grade.values()) {
            assertThat(PracticalWeights.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PracticalWeights.QUEST_ID).isEqualTo("q_practical_weights");
    }
}
