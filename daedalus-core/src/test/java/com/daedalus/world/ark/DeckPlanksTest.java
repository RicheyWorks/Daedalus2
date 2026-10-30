// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import org.junit.jupiter.api.Test;

class DeckPlanksTest {

    private static long brute(int[][] g, int pos, int[] next) {
        int m = g.length;
        int n = g[0].length;
        while (pos < m * n && g[pos / n][pos % n] != 0) {
            pos++;
        }
        if (pos == m * n) {
            assertThat(DeckPlanks.isLayout(g)).isTrue();
            return 1;
        }
        int r = pos / n;
        int c = pos % n;
        long total = 0;
        int id = next[0]++;
        if (c + 1 < n && g[r][c + 1] == 0) {
            g[r][c] = id;
            g[r][c + 1] = id;
            total += brute(g, pos + 1, next);
            g[r][c] = 0;
            g[r][c + 1] = 0;
        }
        if (r + 1 < m) {
            g[r][c] = id;
            g[r + 1][c] = id;
            total += brute(g, pos + 1, next);
            g[r][c] = 0;
            g[r + 1][c] = 0;
        }
        return total;
    }

    @Test
    void countMatchesBacktrackingTiler() {
        for (int m = 1; m <= 6; m++) {
            for (int n = 1; n <= 6; n++) {
                long want = brute(new int[m][n], 0, new int[] {1});
                assertThat(DeckPlanks.count(m, n)).isEqualTo(BigInteger.valueOf(want));
            }
        }
    }

    @Test
    void knownCounts() {
        assertThat(DeckPlanks.count(8, 8)).isEqualTo(BigInteger.valueOf(12_988_816L));
        assertThat(DeckPlanks.count(2, 10)).isEqualTo(BigInteger.valueOf(89));
        assertThat(DeckPlanks.count(3, 5)).isEqualTo(BigInteger.ZERO);
    }

    @Test
    void questAndGuards() {
        assertThat(DeckPlanks.QUEST_ID).isEqualTo("q_deck_planks");
        assertThat(DeckPlanks.quest(2, 3, BigInteger.valueOf(3))).isTrue();
        assertThat(DeckPlanks.quest(2, 3, BigInteger.valueOf(4))).isFalse();
        assertThat(DeckPlanks.isLayout(new int[][] {{1, 1}, {2, 2}})).isTrue();
        assertThat(DeckPlanks.isLayout(new int[][] {{1, 2}, {2, 1}})).isFalse();
        assertThatThrownBy(() -> DeckPlanks.count(13, 13)).isInstanceOf(IllegalArgumentException.class);
    }
}