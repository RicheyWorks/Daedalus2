// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RankLadderTest {

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

    private static int[][] signsFrom(int[][] g, SplittableRandom rnd) {
        int n = g.length;
        List<int[]> s = new ArrayList<>();
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                if (c + 1 < n && rnd.nextInt(3) == 0) {
                    s.add(g[r][c] > g[r][c + 1] ? new int[] {r, c, r, c + 1} : new int[] {r, c + 1, r, c});
                }
                if (r + 1 < n && rnd.nextInt(3) == 0) {
                    s.add(g[r][c] > g[r + 1][c] ? new int[] {r, c, r + 1, c} : new int[] {r + 1, c, r, c});
                }
            }
        }
        return s.toArray(new int[0][]);
    }

    @Test
    void countMatchesBruteForceOverLatinSquares() {
        SplittableRandom rnd = new SplittableRandom(375);
        for (int n = 1; n <= 4; n++) {
            List<int[][]> all = new ArrayList<>();
            latins(n, new int[n][n], 0, all);
            for (int t = 0; t < 40; t++) {
                int[][] hidden = all.get(rnd.nextInt(all.size()));
                int[][] signs = signsFrom(hidden, rnd);
                int[][] given = new int[n][n];
                if (rnd.nextBoolean()) {
                    given[0][0] = hidden[0][0];
                }
                int want = 0;
                for (int[][] g : all) {
                    if (RankLadder.isSolution(given, signs, g)) {
                        want++;
                    }
                }
                assertThat(want).isPositive();
                assertThat(RankLadder.count(given, signs, 1000)).isEqualTo(want);
                assertThat(RankLadder.isSolution(given, signs, RankLadder.solve(given, signs))).isTrue();
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
        int[][] signs = signsFrom(g, new SplittableRandom(5));
        assertThat(RankLadder.quest(new int[5][5], signs, RankLadder.solve(new int[5][5], signs))).isTrue();
    }

    @Test
    void questAndGuards() {
        assertThat(RankLadder.QUEST_ID).isEqualTo("q_rank_ladder");
        int[][] signs = {{0, 1, 0, 0}};
        assertThat(RankLadder.quest(new int[2][2], signs, new int[][] {{1, 2}, {2, 1}})).isTrue();
        assertThat(RankLadder.quest(new int[2][2], signs, new int[][] {{2, 1}, {1, 2}})).isFalse();
        assertThatThrownBy(() -> RankLadder.count(new int[2][2], new int[][] {{0, 0, 1, 1}}, 1))
                .isInstanceOf(IllegalArgumentException.class);
    }
}