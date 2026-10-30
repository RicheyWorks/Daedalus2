// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.SlagFloorTally.Grade;
import com.daedalus.world.forge.SlagFloorTally.Plot;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SlagFloorTallyTest {

    private static long brute(long[][] g, int r1, int c1, int r2, int c2) {
        long s = 0;
        for (int r = r1; r <= r2; r++) {
            for (int c = c1; c <= c2; c++) {
                s += g[r][c];
            }
        }
        return s;
    }

    @Test
    void sumsAndPlotsMatchBruteForce() {
        for (long seed = 0; seed < 60; seed++) {
            int rows = 1 + (int) (seed % 9);
            int cols = 1 + (int) ((seed * 7) % 8);
            long[][] g = SlagFloorTally.floor(seed, rows, cols, 20);
            SlagFloorTally t = new SlagFloorTally(g);
            for (int r1 = 0; r1 < rows; r1++) {
                for (int c1 = 0; c1 < cols; c1++) {
                    for (int r2 = r1; r2 < rows; r2++) {
                        for (int c2 = c1; c2 < cols; c2++) {
                            assertThat(t.sum(r1, c1, r2, c2)).isEqualTo(brute(g, r1, c1, r2, c2));
                        }
                    }
                }
            }
            for (int k = 1; k <= Math.min(rows, cols); k++) {
                long best = Long.MIN_VALUE;
                for (int r = 0; r + k <= rows; r++) {
                    for (int c = 0; c + k <= cols; c++) {
                        best = Math.max(best, brute(g, r, c, r + k - 1, c + k - 1));
                    }
                }
                Plot p = t.bestPlot(k);
                assertThat(p.slag()).as("seed %d k %d", seed, k).isEqualTo(best);
                assertThat(t.grade(k, p.row(), p.col())).isEqualTo(Grade.SWEPT);
            }
        }
    }

    @Test
    void knownFloorAndBadInput() {
        long[][] g = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};
        SlagFloorTally t = new SlagFloorTally(g);
        assertThat(t.sum(0, 0, 2, 2)).isEqualTo(45);
        assertThat(t.sum(1, 1, 2, 2)).isEqualTo(28);
        assertThat(t.bestPlot(2)).isEqualTo(new Plot(1, 1, 28));
        assertThatThrownBy(() -> t.sum(2, 0, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.bestPlot(4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SlagFloorTally(new long[][] {{1}, {1, 2}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        SlagFloorTally t = new SlagFloorTally(new long[][] {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}});
        assertThat(t.grade(2, 1, 1)).isEqualTo(Grade.SWEPT);
        assertThat(t.grade(2, 0, 0)).isEqualTo(Grade.DUSTY);
        assertThat(t.grade(2, 2, 2)).isEqualTo(Grade.DUSTY);
        for (Grade g : Grade.values()) {
            assertThat(SlagFloorTally.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SlagFloorTally.QUEST_ID).isEqualTo("q_slag_floor_tally");
        assertThat(SlagFloorTally.floor(3, 4, 5, 9)).isDeepEqualTo(SlagFloorTally.floor(3, 4, 5, 9));
        assertThatThrownBy(() -> SlagFloorTally.floor(1, -1, 2, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
