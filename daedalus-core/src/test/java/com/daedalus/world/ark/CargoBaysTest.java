// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CargoBaysTest {

    /** Try every number 1..rows*cols in every blank cell. */
    private static long brute(int[][] givens) {
        int h = givens.length;
        int w = givens[0].length;
        int n = h * w;
        int[] blanks = new int[n];
        int k = 0;
        for (int i = 0; i < n; i++) {
            if (givens[i / w][i % w] == 0) {
                blanks[k++] = i;
            }
        }
        long total = 1;
        for (int i = 0; i < k; i++) {
            total *= n;
        }
        int[][] b = new int[h][];
        for (int r = 0; r < h; r++) {
            b[r] = givens[r].clone();
        }
        long found = 0;
        for (long code = 0; code < total; code++) {
            long x = code;
            for (int i = 0; i < k; i++) {
                b[blanks[i] / w][blanks[i] % w] = (int) (x % n) + 1;
                x /= n;
            }
            if (CargoBays.isValid(givens, b)) {
                found++;
            }
        }
        return found;
    }

    @Test
    void blankSmallBoardsMatchBruteForce() {
        assertThat(CargoBays.count(new int[1][1], 10)).isEqualTo(1)
            .isEqualTo(brute(new int[1][1]));
        assertThat(CargoBays.count(new int[1][4], 100)).isEqualTo(brute(new int[1][4]));
        assertThat(CargoBays.count(new int[2][2], 100)).isEqualTo(brute(new int[2][2]));
        assertThat(CargoBays.count(new int[2][3], 1000)).isEqualTo(brute(new int[2][3]));
    }

    @Test
    void givenBoardsMatchBruteForce() {
        SplittableRandom rnd = new SplittableRandom(403);
        int solvable = 0;
        for (int t = 0; t < 25; t++) {
            int h = rnd.nextInt(2, 4);
            int w = 3;
            int[][] g = new int[h][w];
            int blanks = h * w;
            while (blanks > 4) {
                int r = rnd.nextInt(h);
                int c = rnd.nextInt(w);
                if (g[r][c] == 0) {
                    g[r][c] = rnd.nextInt(1, 5);
                    blanks--;
                }
            }
            long want = brute(g);
            if (want > 0) {
                solvable++;
            }
            assertThat(CargoBays.count(g, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            assertThat(CargoBays.solve(g).length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isPositive();
    }

    @Test
    void solveAndQuestFiveByFive() {
        int[][] seed = new int[5][5];
        seed[2][2] = 5;
        seed[0][0] = 3;
        seed[4][4] = 4;
        int[][] full = CargoBays.solve(seed);
        assertThat(full).hasNumberOfRows(5);
        assertThat(CargoBays.quest(seed, full)).isTrue();
        int[][] g = new int[5][5];
        for (int r = 0; r < 5; r++) {
            for (int c = 0; c < 5; c++) {
                if (((r + c) & 1) == 0) {
                    g[r][c] = full[r][c];
                }
            }
        }
        int[][] s = CargoBays.solve(g);
        assertThat(CargoBays.quest(g, s)).isTrue();
        assertThat(s[2][2]).isEqualTo(5);
        s[0][0] = s[0][0] == 1 ? 2 : 1;
        assertThat(CargoBays.quest(g, s)).isFalse();
        assertThat(CargoBays.QUEST_ID).isEqualTo("q_cargo_bays");
        assertThatThrownBy(() -> CargoBays.count(new int[6][1], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}