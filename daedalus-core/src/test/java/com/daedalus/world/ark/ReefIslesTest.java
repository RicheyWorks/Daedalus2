// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ReefIslesTest {

    private static long brute(int[][] clues) {
        int r = clues.length;
        int c = clues[0].length;
        long n = 0;
        boolean[][] w = new boolean[r][c];
        for (int mask = 0; mask < (1 << (r * c)); mask++) {
            for (int i = 0; i < r * c; i++) {
                w[i / c][i % c] = (mask >> i & 1) != 0;
            }
            if (ReefIsles.isValid(clues, w)) {
                n++;
            }
        }
        return n;
    }

    @Test
    void countMatchesBruteForceOverEveryShading() {
        SplittableRandom rnd = new SplittableRandom(385);
        int solvable = 0;
        for (int t = 0; t < 80; t++) {
            int r = rnd.nextInt(1, 5);
            int c = rnd.nextInt(1, 5);
            int[][] clues = new int[r][c];
            int marks = rnd.nextInt(1, 4);
            for (int k = 0; k < marks; k++) {
                clues[rnd.nextInt(r)][rnd.nextInt(c)] = rnd.nextInt(1, Math.min(4, r * c) + 1);
            }
            long want = brute(clues);
            if (want > 0) {
                solvable++;
            }
            assertThat(ReefIsles.count(clues, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            boolean[][] s = ReefIsles.solve(clues);
            assertThat(s.length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isGreaterThan(5);
    }

    @Test
    void solvesFourByFiveAndQuest() {
        int[][] clues = {
            {2, 0, 0, 0, 1},
            {0, 0, 0, 0, 0},
            {0, 0, 3, 0, 0},
            {1, 0, 0, 0, 2}};
        boolean[][] s = ReefIsles.solve(clues);
        assertThat(s).hasNumberOfRows(4);
        assertThat(ReefIsles.quest(clues, s)).isTrue();
        boolean[][] bad = new boolean[4][5];
        assertThat(ReefIsles.quest(clues, bad)).isFalse();
        assertThat(ReefIsles.QUEST_ID).isEqualTo("q_reef_isles");
    }

    @Test
    void rejectsOversize() {
        assertThatThrownBy(() -> ReefIsles.count(new int[5][5], 1))
            .isInstanceOf(IllegalArgumentException.class);
        assertThat(ReefIsles.count(new int[][] {{1, 1}}, 10)).isEqualTo(0);
    }
}