// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MastHeightsTest {

    private static void latins(int n, int[][] g, int cell, List<int[][]> out) {
        if (cell == n * n) {
            int[][] copy = new int[n][];
            for (int i = 0; i < n; i++) {
                copy[i] = g[i].clone();
            }
            out.add(copy);
            return;
        }
        int r = cell / n;
        int c = cell % n;
        for (int v = 1; v <= n; v++) {
            boolean ok = true;
            for (int k = 0; k < c && ok; k++) {
                ok = g[r][k] != v;
            }
            for (int k = 0; k < r && ok; k++) {
                ok = g[k][c] != v;
            }
            if (ok) {
                g[r][c] = v;
                latins(n, g, cell + 1, out);
            }
        }
    }

    @Test
    void countMatchesBruteForceOverLatinSquares() {
        for (int n = 1; n <= 4; n++) {
            List<int[][]> all = new ArrayList<>();
            latins(n, new int[n][n], 0, all);
            Map<String, Integer> byClues = new HashMap<>();
            for (int[][] g : all) {
                byClues.merge(Arrays.deepToString(MastHeights.clues(g)), 1, Integer::sum);
            }
            for (int[][] g : all) {
                int[][] cl = MastHeights.clues(g);
                assertThat(MastHeights.count(cl, 1000)).isEqualTo(byClues.get(Arrays.deepToString(cl)));
                assertThat(MastHeights.quest(cl, MastHeights.solve(cl))).isTrue();
            }
        }
    }

    @Test
    void fiveByFiveSolves() {
        int[][] g = new int[5][5];
        for (int r = 0; r < 5; r++) {
            for (int c = 0; c < 5; c++) {
                g[r][c] = (r * 2 + c) % 5 + 1;
            }
        }
        int[][] cl = MastHeights.clues(g);
        assertThat(MastHeights.quest(cl, MastHeights.solve(cl))).isTrue();
        assertThat(MastHeights.count(new int[4][5], 2)).isEqualTo(2);
    }

    @Test
    void questAndGuards() {
        assertThat(MastHeights.QUEST_ID).isEqualTo("q_mast_heights");
        assertThat(MastHeights.visible(new int[] {2, 1, 3})).isEqualTo(2);
        int[][] g = {{1, 2}, {2, 1}};
        assertThat(MastHeights.quest(MastHeights.clues(g), g)).isTrue();
        assertThat(MastHeights.quest(MastHeights.clues(g), new int[][] {{2, 1}, {1, 2}})).isFalse();
        assertThatThrownBy(() -> MastHeights.count(new int[4][6], 1)).isInstanceOf(IllegalArgumentException.class);
    }
}