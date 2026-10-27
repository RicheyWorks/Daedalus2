// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class LanternShadeTest {

    @Test
    void countMatchesBruteForceOverEveryShading() {
        SplittableRandom rnd = new SplittableRandom(377);
        for (int t = 0; t < 60; t++) {
            int n = rnd.nextInt(2, 5);
            int[][] g = new int[n][n];
            for (int[] row : g) {
                for (int c = 0; c < n; c++) {
                    row[c] = rnd.nextInt(1, n + 1);
                }
            }
            int want = 0;
            for (int mask = 0; mask < (1 << (n * n)); mask++) {
                boolean[][] sh = new boolean[n][n];
                for (int i = 0; i < n * n; i++) {
                    sh[i / n][i % n] = (mask >> i & 1) != 0;
                }
                if (LanternShade.isValid(g, sh)) {
                    want++;
                }
            }
            assertThat(LanternShade.count(g, 100_000)).isEqualTo(want);
            boolean[][] got = LanternShade.solve(g);
            assertThat(got.length > 0).isEqualTo(want > 0);
            if (want > 0) {
                assertThat(LanternShade.isValid(g, got)).isTrue();
            }
        }
    }

    @Test
    void sixBySixFromLatinSquare() {
        int[][] g = new int[6][6];
        for (int r = 0; r < 6; r++) {
            for (int c = 0; c < 6; c++) {
                g[r][c] = (r + c) % 6 + 1;
            }
        }
        g[0][1] = g[0][3];
        g[2][4] = g[2][0];
        g[5][2] = g[5][5];
        boolean[][] sh = LanternShade.solve(g);
        assertThat(LanternShade.quest(g, sh)).isTrue();
    }

    @Test
    void questAndGuards() {
        assertThat(LanternShade.QUEST_ID).isEqualTo("q_lantern_shade");
        int[][] g = {{1, 1}, {2, 1}};
        assertThat(LanternShade.quest(g, new boolean[][] {{false, true}, {false, false}})).isTrue();
        assertThat(LanternShade.quest(g, new boolean[][] {{false, false}, {false, false}})).isFalse();
        assertThatThrownBy(() -> LanternShade.count(new int[7][7], 1)).isInstanceOf(IllegalArgumentException.class);
    }
}