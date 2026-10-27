// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class PoleStarsTest {

    private static long bruteCells(int[][] regions) {
        int n = regions.length;
        long found = 0;
        int[][] b = new int[n][n];
        for (int mask = 0; mask < (1 << (n * n)); mask++) {
            for (int i = 0; i < n * n; i++) {
                b[i / n][i % n] = mask >> i & 1;
            }
            if (PoleStars.isValid(regions, b)) {
                found++;
            }
        }
        return found;
    }

    private static long brutePerms(int[][] regions) {
        int n = regions.length;
        long found = 0;
        long total = 1;
        for (int i = 0; i < n; i++) {
            total *= n;
        }
        int[][] b = new int[n][n];
        for (long code = 0; code < total; code++) {
            long x = code;
            for (int r = 0; r < n; r++) {
                Arrays.fill(b[r], 0);
                b[r][(int) (x % n)] = 1;
                x /= n;
            }
            if (PoleStars.isValid(regions, b)) {
                found++;
            }
        }
        return found;
    }

    private static int[][] randomRegions(SplittableRandom rnd, int n) {
        int[][] g = new int[n][n];
        for (int[] row : g) {
            for (int c = 0; c < n; c++) {
                row[c] = rnd.nextInt(n);
            }
        }
        return g;
    }

    @Test
    void countMatchesBruteForceOverEveryBoardUpToFour() {
        SplittableRandom rnd = new SplittableRandom(399);
        for (int n = 1; n <= 4; n++) {
            for (int t = 0; t < 10; t++) {
                int[][] g = randomRegions(rnd, n);
                long want = bruteCells(g);
                assertThat(PoleStars.count(g, Long.MAX_VALUE)).as("n%d t%d", n, t)
                    .isEqualTo(want);
                assertThat(PoleStars.solve(g).length == 0).isEqualTo(want == 0);
            }
        }
    }

    @Test
    void countMatchesRowBruteForceForFiveAndSix() {
        SplittableRandom rnd = new SplittableRandom(4399);
        for (int n = 5; n <= 6; n++) {
            int[][] cols = new int[n][n];
            for (int r = 0; r < n; r++) {
                for (int c = 0; c < n; c++) {
                    cols[r][c] = c;
                }
            }
            assertThat(PoleStars.count(cols, Long.MAX_VALUE)).isEqualTo(brutePerms(cols));
            for (int t = 0; t < 5; t++) {
                int[][] g = randomRegions(rnd, n);
                assertThat(PoleStars.count(g, Long.MAX_VALUE)).isEqualTo(brutePerms(g));
            }
        }
    }

    @Test
    void solveAndQuestEightByEight() {
        int[] at = {0, 2, 4, 6, 1, 3, 5, 7};
        int[][] g = new int[8][8];
        for (int r = 0; r < 8; r++) {
            for (int c = 0; c < 8; c++) {
                int best = 0;
                for (int k = 1; k < 8; k++) {
                    if (Math.abs(k - r) + Math.abs(at[k] - c)
                        < Math.abs(best - r) + Math.abs(at[best] - c)) {
                        best = k;
                    }
                }
                g[r][c] = best;
            }
        }
        int[][] s = PoleStars.solve(g);
        assertThat(s).hasNumberOfRows(8);
        assertThat(PoleStars.quest(g, s)).isTrue();
        s[0][0] ^= 1;
        assertThat(PoleStars.quest(g, s)).isFalse();
        assertThat(PoleStars.QUEST_ID).isEqualTo("q_pole_stars");
        assertThatThrownBy(() -> PoleStars.count(new int[9][9], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}