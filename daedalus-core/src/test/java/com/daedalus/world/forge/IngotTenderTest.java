// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.IngotTender.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IngotTenderTest {

    private static long bruteWays(int[] c, int i, int left) {
        if (left == 0) {
            return 1;
        }
        if (i == c.length) {
            return 0;
        }
        long w = 0;
        for (int k = 0; k * c[i] <= left; k++) {
            w += bruteWays(c, i + 1, left - k * c[i]);
        }
        return w;
    }

    private static int bruteMin(int[] c, int i, int left) {
        if (left == 0) {
            return 0;
        }
        if (i == c.length) {
            return Integer.MAX_VALUE;
        }
        int best = Integer.MAX_VALUE;
        for (int k = 0; k * c[i] <= left; k++) {
            int rest = bruteMin(c, i + 1, left - k * c[i]);
            if (rest != Integer.MAX_VALUE) {
                best = Math.min(best, rest + k);
            }
        }
        return best;
    }

    @Test
    void minAndWaysMatchBruteForce() {
        for (long seed = 0; seed < 120; seed++) {
            int[] c = IngotTender.purse(seed, 1 + (int) (seed % 4), 12);
            for (int a = 0; a <= 40; a++) {
                int m = bruteMin(c, 0, a);
                assertThat(IngotTender.minIngots(c, a)).as("seed %d a %d", seed, a)
                        .isEqualTo(m == Integer.MAX_VALUE ? IngotTender.IMPOSSIBLE : m);
                assertThat(IngotTender.ways(c, a)).isEqualTo(bruteWays(c, 0, a));
            }
        }
    }

    @Test
    void greedyCounterexampleMatchesExhaustiveScan() {
        for (long seed = 0; seed < 200; seed++) {
            int[] c = IngotTender.purse(seed, 1 + (int) (seed % 4), 15);
            int first = -1;
            for (int a = 1; a <= 260 && first < 0; a++) {
                if (IngotTender.greedy(c, a) != IngotTender.minIngots(c, a)) {
                    first = a;
                }
            }
            assertThat(IngotTender.greedyCounterexample(c)).as("seed %d", seed).isEqualTo(first);
        }
        assertThat(IngotTender.greedyCounterexample(new int[] {1, 3, 4})).isEqualTo(6);
        assertThat(IngotTender.greedyCounterexample(new int[] {1, 5, 10, 25})).isEqualTo(-1);
        assertThat(IngotTender.greedyCounterexample(new int[] {3, 5})).isEqualTo(6);
    }

    @Test
    void badInputGradesLinesAndReplay() {
        assertThatThrownBy(() -> IngotTender.minIngots(new int[] {0}, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotTender.ways(new int[] {1}, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotTender.greedyCounterexample(new int[0]))
                .isInstanceOf(IllegalArgumentException.class);
        int[] c = {1, 3, 4};
        assertThat(IngotTender.grade(c, 6, new int[] {3, 3})).isEqualTo(Grade.EXACT);
        assertThat(IngotTender.grade(c, 6, new int[] {4, 1, 1})).isEqualTo(Grade.CLUMSY);
        assertThat(IngotTender.grade(c, 6, new int[] {2, 4})).isEqualTo(Grade.CLUMSY);
        assertThat(IngotTender.grade(c, 6, new int[] {3, 4})).isEqualTo(Grade.CLUMSY);
        for (Grade g : Grade.values()) {
            assertThat(IngotTender.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(IngotTender.QUEST_ID).isEqualTo("q_ingot_tender");
        assertThat(IngotTender.purse(3, 4, 20)).isEqualTo(IngotTender.purse(3, 4, 20)).hasSize(4).isSorted();
        assertThatThrownBy(() -> IngotTender.purse(1, 5, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
