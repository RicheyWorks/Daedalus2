// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class DeckLightsTest {

    private static final int O = DeckLights.OPEN;
    private static final int W = DeckLights.WALL;

    private static long brute(int[][] grid) {
        int h = grid.length;
        int w = grid[0].length;
        long found = 0;
        int[][] b = new int[h][w];
        for (int mask = 0; mask < (1 << (h * w)); mask++) {
            for (int i = 0; i < h * w; i++) {
                b[i / w][i % w] = mask >> i & 1;
            }
            if (DeckLights.isValid(grid, b)) {
                found++;
            }
        }
        return found;
    }

    private static int[][] randomGrid(SplittableRandom rnd, int h, int w) {
        int[][] g = new int[h][w];
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                int x = rnd.nextInt(10);
                g[r][c] = x < 6 ? O : x < 8 ? W : rnd.nextInt(3);
            }
        }
        return g;
    }

    @Test
    void countMatchesBruteForceOnSmallBoards() {
        SplittableRandom rnd = new SplittableRandom(396);
        int solvable = 0;
        for (int t = 0; t < 60; t++) {
            int h = rnd.nextInt(1, 5);
            int w = rnd.nextInt(1, 5);
            int[][] g = randomGrid(rnd, h, w);
            long want = brute(g);
            if (want > 0) {
                solvable++;
            }
            assertThat(DeckLights.count(g, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            assertThat(DeckLights.solve(g).length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isPositive();
    }

    @Test
    void openFourByFourHasTwentyFourRookBoards() {
        int[][] g = new int[4][4];
        for (int[] row : g) {
            Arrays.fill(row, O);
        }
        assertThat(DeckLights.count(g, Long.MAX_VALUE)).isEqualTo(24).isEqualTo(brute(g));
    }

    private static boolean lit(int[][] g, int[][] lamps, int r, int c) {
        int[] dr = {-1, 1, 0, 0};
        int[] dc = {0, 0, -1, 1};
        for (int k = 0; k < 4; k++) {
            int rr = r + dr[k];
            int cc = c + dc[k];
            while (rr >= 0 && rr < g.length && cc >= 0 && cc < g[0].length && g[rr][cc] == O) {
                if (lamps[rr][cc] == 1) {
                    return true;
                }
                rr += dr[k];
                cc += dc[k];
            }
        }
        return false;
    }

    @Test
    void solveAndQuestSevenBySeven() {
        int n = 9;
        int[][] g = {
            {O, O, O, W, O, O, O},
            {O, n, O, O, O, n, O},
            {O, O, O, O, O, O, O},
            {W, O, O, n, O, O, W},
            {O, O, O, O, O, O, O},
            {O, n, O, O, O, W, O},
            {O, O, O, W, O, O, O},
        };
        int[][] lamps = new int[7][7];
        lamps[2][3] = 1;
        lamps[4][3] = 1;
        lamps[3][2] = 1;
        lamps[3][4] = 1;
        for (int r = 0; r < 7; r++) {
            for (int c = 0; c < 7; c++) {
                if (g[r][c] == O && lamps[r][c] == 0 && !lit(g, lamps, r, c)) {
                    lamps[r][c] = 1;
                }
            }
        }
        for (int r = 0; r < 7; r++) {
            for (int c = 0; c < 7; c++) {
                if (g[r][c] == n) {
                    g[r][c] = (r > 0 ? lamps[r - 1][c] : 0) + (r < 6 ? lamps[r + 1][c] : 0)
                        + (c > 0 ? lamps[r][c - 1] : 0) + (c < 6 ? lamps[r][c + 1] : 0);
                }
            }
        }
        assertThat(DeckLights.isValid(g, lamps)).isTrue();
        assertThat(g[3][3]).isEqualTo(4);
        int[][] s = DeckLights.solve(g);
        assertThat(s).hasNumberOfRows(7);
        assertThat(DeckLights.quest(g, s)).isTrue();
        assertThat(s[2][3] + s[4][3] + s[3][2] + s[3][4]).isEqualTo(4);
        s[0][0] ^= 1;
        assertThat(DeckLights.quest(g, s)).isFalse();
        assertThat(DeckLights.QUEST_ID).isEqualTo("q_deck_lights");
        assertThatThrownBy(() -> DeckLights.count(new int[8][1], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}