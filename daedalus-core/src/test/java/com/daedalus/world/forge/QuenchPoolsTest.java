// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.QuenchPools.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class QuenchPoolsTest {

    private static long brute1d(int[] h) {
        long w = 0;
        for (int i = 0; i < h.length; i++) {
            int l = 0;
            int r = 0;
            for (int j = 0; j <= i; j++) {
                l = Math.max(l, h[j]);
            }
            for (int j = i; j < h.length; j++) {
                r = Math.max(r, h[j]);
            }
            w += Math.min(l, r) - h[i];
        }
        return w;
    }

    /** Brute force 2D: interior starts at the max height; relax level = max(h, min neighbour) to a fixed point. */
    private static long brute2d(int[][] g) {
        int rows = g.length;
        int cols = g[0].length;
        int top = 0;
        for (int[] row : g) {
            for (int x : row) {
                top = Math.max(top, x);
            }
        }
        int[][] lv = new int[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                boolean rim = i == 0 || j == 0 || i == rows - 1 || j == cols - 1;
                lv[i][j] = rim ? g[i][j] : top;
            }
        }
        boolean changed = true;
        while (changed) {
            changed = false;
            for (int i = 1; i < rows - 1; i++) {
                for (int j = 1; j < cols - 1; j++) {
                    int m = Math.min(Math.min(lv[i - 1][j], lv[i + 1][j]), Math.min(lv[i][j - 1], lv[i][j + 1]));
                    int nv = Math.max(g[i][j], m);
                    if (nv < lv[i][j]) {
                        lv[i][j] = nv;
                        changed = true;
                    }
                }
            }
        }
        long w = 0;
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                w += lv[i][j] - g[i][j];
            }
        }
        return w;
    }

    @Test
    void rowVolumeMatchesBruteForceOnSeededYards() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] h = QuenchPools.heaps(seed, (int) (seed % 30), (int) (seed % 12));
            assertThat(QuenchPools.trapped(h)).as("seed %d", seed).isEqualTo(brute1d(h));
            long sum = 0;
            for (int d : QuenchPools.depths(h)) {
                sum += d;
            }
            assertThat(sum).isEqualTo(QuenchPools.trapped(h));
        }
    }

    @Test
    void gridVolumeMatchesRelaxationOnSeededYards() {
        for (long seed = 1; seed <= 200; seed++) {
            int[][] g = QuenchPools.yard(seed, 1 + (int) (seed % 8), 1 + (int) (seed % 9), 1 + (int) (seed % 10));
            assertThat(QuenchPools.trapped2d(g)).as("seed %d", seed).isEqualTo(brute2d(g));
        }
    }

    @Test
    void handWorkedYards() {
        assertThat(QuenchPools.trapped(new int[] {0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1})).isEqualTo(6);
        assertThat(QuenchPools.trapped(new int[] {4, 2, 0, 3, 2, 5})).isEqualTo(9);
        int[][] g = {{1, 4, 3, 1, 3, 2}, {3, 2, 1, 3, 2, 4}, {2, 3, 3, 2, 3, 1}};
        assertThat(QuenchPools.trapped2d(g)).isEqualTo(4);
        assertThat(QuenchPools.trapped(new int[0])).isZero();
        assertThat(QuenchPools.trapped2d(new int[0][])).isZero();
    }

    @Test
    void gradesAndLines() {
        int[] h = {4, 2, 0, 3, 2, 5};
        assertThat(QuenchPools.grade(h, 2)).isEqualTo(Grade.FULL);
        assertThat(QuenchPools.grade(h, 1)).isEqualTo(Grade.SHALLOW);
        assertThat(QuenchPools.grade(h, 0)).isEqualTo(Grade.DRY);
        assertThat(QuenchPools.forgemasterLine(Grade.DRY)).contains("alight");
        assertThatThrownBy(() -> QuenchPools.grade(h, 6)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void sameSeedReplaysAndRejects() {
        assertThat(QuenchPools.heaps(221L, 20, 9)).isEqualTo(QuenchPools.heaps(221L, 20, 9));
        assertThat(QuenchPools.yard(221L, 5, 6, 9)).isDeepEqualTo(QuenchPools.yard(221L, 5, 6, 9));
        assertThat(QuenchPools.QUEST_ID).isEqualTo("q_quench_pools");
        assertThatThrownBy(() -> QuenchPools.heaps(1L, -1, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> QuenchPools.trapped2d(new int[][] {{1, 2}, {1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
