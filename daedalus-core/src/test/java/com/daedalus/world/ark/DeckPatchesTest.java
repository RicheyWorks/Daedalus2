// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class DeckPatchesTest {

    /** Fixed patches touching row 0 and column 0 of an n x n grid, by brute-force subset choice. */
    private static long bruteFixed(int n) {
        int cellsTotal = n * n;
        return choose(n, cellsTotal, 0, 0, new int[n]);
    }

    private static long choose(int n, int total, int start, int depth, int[] pick) {
        if (depth == n) {
            int[][] cells = new int[n][];
            boolean row0 = false;
            boolean col0 = false;
            for (int i = 0; i < n; i++) {
                cells[i] = new int[] {pick[i] / n, pick[i] % n};
                row0 |= cells[i][0] == 0;
                col0 |= cells[i][1] == 0;
            }
            return row0 && col0 && DeckPatches.isPatch(cells) ? 1 : 0;
        }
        long c = 0;
        for (int i = start; i < total; i++) {
            pick[depth] = i;
            c += choose(n, total, i + 1, depth + 1, pick);
        }
        return c;
    }

    @Test
    void fixedCountMatchesBruteForceGridSubsets() {
        for (int n = 1; n <= 6; n++) {
            assertThat(DeckPatches.fixedCount(n)).isEqualTo(bruteFixed(n));
        }
    }

    @Test
    void knownFreeAndFixedCounts() {
        long[] free = {1, 1, 2, 5, 12, 35, 108, 369, 1285};
        long[] fixed = {1, 2, 6, 19, 63, 216, 760, 2725, 9910};
        for (int n = 1; n <= 9; n++) {
            assertThat(DeckPatches.freeCount(n)).isEqualTo(free[n - 1]);
            assertThat(DeckPatches.fixedCount(n)).isEqualTo(fixed[n - 1]);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(DeckPatches.QUEST_ID).isEqualTo("q_deck_patches");
        assertThat(DeckPatches.quest(5, 12)).isTrue();
        assertThat(DeckPatches.quest(5, 18)).isFalse();
        assertThat(DeckPatches.isPatch(new int[][] {{0, 0}, {0, 1}, {1, 1}})).isTrue();
        assertThat(DeckPatches.isPatch(new int[][] {{0, 0}, {1, 1}})).isFalse();
        assertThatThrownBy(() -> DeckPatches.freeCount(11)).isInstanceOf(IllegalArgumentException.class);
    }
}