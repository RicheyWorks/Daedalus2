// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SailPatternTest {

    private static int[][] grid(int mask, int h, int w) {
        int[][] g = new int[h][w];
        for (int i = 0; i < h * w; i++) {
            g[i / w][i % w] = mask >> i & 1;
        }
        return g;
    }

    @Test
    void countMatchesBruteForceOverEvery4x4() {
        Map<String, Integer> byClues = new HashMap<>();
        for (int mask = 0; mask < (1 << 16); mask++) {
            int[][] g = grid(mask, 4, 4);
            String k = Arrays.deepToString(SailPattern.rowClues(g)) + Arrays.deepToString(SailPattern.colClues(g));
            byClues.merge(k, 1, Integer::sum);
        }
        for (int mask = 0; mask < (1 << 16); mask += 37) {
            int[][] g = grid(mask, 4, 4);
            int[][] rows = SailPattern.rowClues(g);
            int[][] cols = SailPattern.colClues(g);
            String k = Arrays.deepToString(rows) + Arrays.deepToString(cols);
            assertThat(SailPattern.count(rows, cols, 1000)).isEqualTo(byClues.get(k));
            assertThat(SailPattern.quest(rows, cols, SailPattern.solve(rows, cols))).isTrue();
        }
    }

    @Test
    void solvesRandom8x8() {
        SplittableRandom rnd = new SplittableRandom(367);
        for (int t = 0; t < 30; t++) {
            int[][] g = new int[8][8];
            for (int[] row : g) {
                for (int c = 0; c < 8; c++) {
                    row[c] = rnd.nextInt(2);
                }
            }
            int[][] rows = SailPattern.rowClues(g);
            int[][] cols = SailPattern.colClues(g);
            assertThat(SailPattern.quest(rows, cols, SailPattern.solve(rows, cols))).isTrue();
        }
    }

    @Test
    void questAndGuards() {
        assertThat(SailPattern.QUEST_ID).isEqualTo("q_sail_pattern");
        int[][] rows = {{1}, {1}};
        int[][] cols = {{1}, {1}};
        assertThat(SailPattern.count(rows, cols, 10)).isEqualTo(2);
        assertThat(SailPattern.quest(rows, cols, new int[][] {{1, 0}, {0, 1}})).isTrue();
        assertThat(SailPattern.quest(rows, cols, new int[][] {{1, 0}, {1, 0}})).isFalse();
        assertThat(SailPattern.solve(new int[][] {{2}}, new int[][] {{}, {}})).isEmpty();
        assertThatThrownBy(() -> SailPattern.count(new int[9][0], cols, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}