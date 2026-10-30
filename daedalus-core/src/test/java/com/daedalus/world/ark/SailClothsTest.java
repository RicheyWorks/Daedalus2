// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SailClothsTest {

    private static final int S = SailCloths.SQUARE;
    private static final int W = SailCloths.WIDE;
    private static final int T = SailCloths.TALL;

    /** Every labelling of every cell with a clue number. */
    private static long brute(int[][] clues) {
        int h = clues.length;
        int w = clues[0].length;
        int k = 0;
        for (int[] row : clues) {
            for (int v : row) {
                if (v != 0) {
                    k++;
                }
            }
        }
        long total = 1;
        for (int i = 0; i < h * w; i++) {
            total *= k;
        }
        int[][] b = new int[h][w];
        long found = 0;
        for (long code = 0; code < total; code++) {
            long x = code;
            for (int i = 0; i < h * w; i++) {
                b[i / w][i % w] = (int) (x % k);
                x /= k;
            }
            if (SailCloths.isValid(clues, b)) {
                found++;
            }
        }
        return found;
    }

    @Test
    void countMatchesBruteForceOnSmallBoards() {
        SplittableRandom rnd = new SplittableRandom(406);
        int solvable = 0;
        for (int t = 0; t < 40; t++) {
            int h = rnd.nextInt(1, 4);
            int w = rnd.nextInt(1, 5);
            int k = rnd.nextInt(1, Math.min(4, h * w + 1));
            if (h * w > 12 || k == 3 && h * w > 10) {
                continue;
            }
            int[][] g = new int[h][w];
            int placed = 0;
            while (placed < k) {
                int r = rnd.nextInt(h);
                int c = rnd.nextInt(w);
                if (g[r][c] == 0) {
                    g[r][c] = rnd.nextInt(1, 4);
                    placed++;
                }
            }
            long want = brute(g);
            if (want > 0) {
                solvable++;
            }
            assertThat(SailCloths.count(g, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            assertThat(SailCloths.solve(g).length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isPositive();
    }

    @Test
    void fourPiecesMeetingAtOnePointIsRefused() {
        int[][] clues = {{S, S}, {S, S}};
        assertThat(SailCloths.isValid(clues, new int[][] {{0, 1}, {2, 3}})).isFalse();
        assertThat(SailCloths.count(clues, Long.MAX_VALUE)).isZero().isEqualTo(brute(clues));
        int[][] one = {{0, W}, {0, 0}};
        assertThat(SailCloths.count(one, Long.MAX_VALUE)).isZero();
        int[][] sq = {{0, 0}, {S, 0}};
        assertThat(SailCloths.solve(sq)).isDeepEqualTo(new int[][] {{0, 0}, {0, 0}});
    }

    @Test
    void solveAndQuestSixBySix() {
        int[][] g = {
            {0, W, 0, 0, 0, 0},
            {0, 0, 0, 0, S, 0},
            {0, 0, 0, 0, 0, 0},
            {0, 0, T, 0, 0, 0},
            {T, 0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, S},
        };
        int[][] known = {
            {0, 0, 0, 1, 1, 1},
            {0, 0, 0, 1, 1, 1},
            {3, 3, 2, 1, 1, 1},
            {3, 3, 2, 4, 4, 4},
            {3, 3, 2, 4, 4, 4},
            {3, 3, 2, 4, 4, 4},
        };
        assertThat(SailCloths.isValid(g, known)).isTrue();
        int[][] s = SailCloths.solve(g);
        assertThat(s).hasNumberOfRows(6);
        assertThat(SailCloths.quest(g, s)).isTrue();
        int[][] bad = new int[6][];
        for (int r = 0; r < 6; r++) {
            bad[r] = s[r].clone();
        }
        bad[0][0] = bad[5][5];
        assertThat(SailCloths.quest(g, bad)).isFalse();
        assertThat(SailCloths.QUEST_ID).isEqualTo("q_sail_cloths");
        assertThatThrownBy(() -> SailCloths.count(new int[7][1], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}