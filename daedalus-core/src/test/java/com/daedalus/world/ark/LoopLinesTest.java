// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class LoopLinesTest {

    private static int[][] randomClues(int r, int c, SplittableRandom rnd) {
        int[][] g = new int[r][c];
        for (int[] row : g) {
            for (int i = 0; i < c; i++) {
                row[i] = rnd.nextInt(3) == 0 ? -1 : rnd.nextInt(0, 4);
            }
        }
        return g;
    }

    private static long brute(int[][] clues) {
        int e = LoopLines.edgeCount(clues.length, clues[0].length);
        long n = 0;
        boolean[] on = new boolean[e];
        for (int mask = 0; mask < (1 << e); mask++) {
            for (int i = 0; i < e; i++) {
                on[i] = (mask >> i & 1) != 0;
            }
            if (LoopLines.isValid(clues, on)) {
                n++;
            }
        }
        return n;
    }

    @Test
    void countMatchesBruteForceOverEveryEdgeSubset() {
        SplittableRandom rnd = new SplittableRandom(381);
        int[][] sizes = {{1, 1}, {1, 2}, {2, 1}, {1, 3}, {2, 2}, {2, 3}, {3, 2}};
        for (int t = 0; t < 21; t++) {
            int[] s = sizes[t % sizes.length];
            int[][] clues = t < sizes.length ? new int[s[0]][s[1]] : randomClues(s[0], s[1], rnd);
            if (t < sizes.length) {
                for (int[] row : clues) {
                    java.util.Arrays.fill(row, -1);
                }
            }
            long want = brute(clues);
            assertThat(LoopLines.count(clues, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            boolean[] sol = LoopLines.solve(clues);
            assertThat(sol.length == 0).isEqualTo(want == 0);
        }
    }

    @Test
    void knownLoopCounts() {
        // simple cycles in grid graphs: 1x1 cell grid 1, 2x2 cells 13, 3x3 cells 213
        assertThat(LoopLines.count(new int[][] {{-1}}, 100)).isEqualTo(1);
        assertThat(LoopLines.count(new int[][] {{-1, -1}, {-1, -1}}, 100)).isEqualTo(13);
        int[][] g3 = {{-1, -1, -1}, {-1, -1, -1}, {-1, -1, -1}};
        assertThat(LoopLines.count(g3, 1000)).isEqualTo(213);
    }

    @Test
    void solvesFourByFourAndQuest() {
        int[][] clues = {{3, 2, 2, 3}, {-1, -1, -1, -1}, {-1, -1, -1, -1}, {3, 2, 2, 3}};
        boolean[] sol = LoopLines.solve(clues);
        assertThat(sol).hasSize(LoopLines.edgeCount(4, 4));
        assertThat(LoopLines.quest(clues, sol)).isTrue();
        boolean[] bad = sol.clone();
        bad[0] = !bad[0];
        assertThat(LoopLines.quest(clues, bad)).isFalse();
        assertThat(LoopLines.count(new int[][] {{0}}, 10)).isZero();
        assertThat(LoopLines.QUEST_ID).isEqualTo("q_loop_lines");
        assertThatThrownBy(() -> LoopLines.count(new int[5][5], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}