// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.IngotRackBanner.Banner;
import com.daedalus.world.forge.IngotRackBanner.Grade;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IngotRackBannerTest {

    private static long bruteHist(int[] h) {
        long best = 0;
        for (int i = 0; i < h.length; i++) {
            int m = Integer.MAX_VALUE;
            for (int j = i; j < h.length; j++) {
                m = Math.min(m, h[j]);
                best = Math.max(best, (long) m * (j - i + 1));
            }
        }
        return best;
    }

    private static long bruteGrid(boolean[][] g) {
        long best = 0;
        int r = g.length;
        int c = g[0].length;
        for (int t = 0; t < r; t++) {
            for (int b = t; b < r; b++) {
                for (int l = 0; l < c; l++) {
                    for (int rr = l; rr < c; rr++) {
                        boolean ok = true;
                        for (int i = t; i <= b && ok; i++) {
                            for (int j = l; j <= rr && ok; j++) {
                                ok = g[i][j];
                            }
                        }
                        if (ok) {
                            best = Math.max(best, (long) (b - t + 1) * (rr - l + 1));
                        }
                    }
                }
            }
        }
        return best;
    }

    @Test
    void largestMatchesBruteForceOnSeededRacks() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] h = IngotRackBanner.stacks(seed, (int) (seed % 35), (int) (seed % 15));
            Banner b = IngotRackBanner.largest(h);
            assertThat(b.area()).as("seed %d", seed).isEqualTo(bruteHist(h));
            if (b.area() > 0) {
                assertThat(IngotRackBanner.grade(h, b)).isEqualTo(Grade.GRAND);
            }
        }
    }

    @Test
    void maximalRectangleMatchesBruteForceOnSeededFloors() {
        for (long seed = 1; seed <= 200; seed++) {
            SplittableRandom r = new SplittableRandom(seed);
            int rows = 1 + (int) (seed % 7);
            int cols = 1 + (int) (seed % 8);
            boolean[][] g = new boolean[rows][cols];
            for (int i = 0; i < rows; i++) {
                for (int j = 0; j < cols; j++) {
                    g[i][j] = r.nextInt(100) < 70;
                }
            }
            assertThat(IngotRackBanner.maximalRectangle(g)).as("seed %d", seed).isEqualTo(bruteGrid(g));
        }
    }

    @Test
    void handWorkedRack() {
        int[] h = {2, 1, 5, 6, 2, 3};
        assertThat(IngotRackBanner.largest(h)).isEqualTo(new Banner(2, 3, 5));
        assertThat(IngotRackBanner.largest(h).area()).isEqualTo(10);
        assertThat(IngotRackBanner.grade(h, new Banner(2, 3, 5))).isEqualTo(Grade.GRAND);
        assertThat(IngotRackBanner.grade(h, new Banner(2, 5, 2))).isEqualTo(Grade.MODEST);
        assertThat(IngotRackBanner.grade(h, new Banner(1, 3, 2))).isEqualTo(Grade.TORN);
        assertThat(IngotRackBanner.grade(h, new Banner(0, 0, 1))).isEqualTo(Grade.TORN);
        assertThat(IngotRackBanner.forgemasterLine(Grade.GRAND)).contains("crest");
    }

    @Test
    void sameSeedReplays() {
        assertThat(IngotRackBanner.stacks(224L, 20, 9)).isEqualTo(IngotRackBanner.stacks(224L, 20, 9));
        assertThat(IngotRackBanner.largest(IngotRackBanner.stacks(224L, 20, 9)))
                .isEqualTo(IngotRackBanner.largest(IngotRackBanner.stacks(224L, 20, 9)));
        assertThat(IngotRackBanner.QUEST_ID).isEqualTo("q_ingot_rack_banner");
    }

    @Test
    void edgesAndRejects() {
        assertThat(IngotRackBanner.largest(new int[0]).area()).isZero();
        assertThat(IngotRackBanner.maximalRectangle(new boolean[0][])).isZero();
        assertThatThrownBy(() -> IngotRackBanner.largest(new int[] {1, -2}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotRackBanner.maximalRectangle(new boolean[][] {{true}, {true, false}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotRackBanner.stacks(1L, -1, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
