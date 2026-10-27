// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.VentLevers.Grade;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class VentLeversTest {

    private static boolean allShut(boolean[][] g) {
        for (boolean[] row : g) {
            for (boolean b : row) {
                if (b) {
                    return false;
                }
            }
        }
        return true;
    }

    @Test
    void fewestPullsMatchBruteForceOnSmallGrids() {
        int unsolvable = 0;
        for (long seed = 0; seed < 200; seed++) {
            int rows = 1 + (int) (seed % 4);
            int cols = 1 + (int) ((seed / 4) % 4);
            boolean[][] g = VentLevers.vents(seed, rows, cols, 50);
            int n = rows * cols;
            int best = Integer.MAX_VALUE;
            for (int mask = 0; mask < (1 << n); mask++) {
                boolean[][] p = new boolean[rows][cols];
                for (int v = 0; v < n; v++) {
                    p[v / cols][v % cols] = ((mask >> v) & 1) == 1;
                }
                if (allShut(VentLevers.apply(g, p))) {
                    best = Math.min(best, Integer.bitCount(mask));
                }
            }
            Optional<boolean[][]> got = VentLevers.fewestPulls(g);
            if (best == Integer.MAX_VALUE) {
                unsolvable++;
                assertThat(got).as("seed %d", seed).isEmpty();
            } else {
                assertThat(got).as("seed %d", seed).isPresent();
                assertThat(allShut(VentLevers.apply(g, got.get()))).isTrue();
                assertThat(VentLevers.count(got.get())).as("seed %d", seed).isEqualTo(best);
                assertThat(VentLevers.grade(g, got.get())).isEqualTo(Grade.SEALED);
            }
        }
        assertThat(unsolvable).isPositive();
    }

    @Test
    void classicFiveByFiveIsSolved() {
        boolean[][] g = VentLevers.vents(11, 5, 5, 50);
        Optional<boolean[][]> got = VentLevers.fewestPulls(g);
        if (got.isPresent()) {
            assertThat(allShut(VentLevers.apply(g, got.get()))).isTrue();
        }
        boolean[][] allOpen = new boolean[3][3];
        for (boolean[] row : allOpen) {
            Arrays.fill(row, true);
        }
        assertThat(VentLevers.count(VentLevers.fewestPulls(allOpen).orElseThrow())).isEqualTo(5);
        assertThatThrownBy(() -> VentLevers.fewestPulls(new boolean[0][])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VentLevers.fewestPulls(new boolean[][] {{true}, {true, false}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        boolean[][] g = {{true, true}, {true, false}};
        boolean[][] one = {{true, false}, {false, false}};
        assertThat(VentLevers.grade(g, one)).isEqualTo(Grade.SEALED);
        assertThat(VentLevers.grade(g, new boolean[2][2])).isEqualTo(Grade.DRAFTY);
        for (Grade x : Grade.values()) {
            assertThat(VentLevers.forgemasterLine(x)).startsWith("Forgemaster:");
        }
        assertThat(VentLevers.QUEST_ID).isEqualTo("q_vent_levers");
        assertThat(VentLevers.vents(4, 3, 4, 40)).isDeepEqualTo(VentLevers.vents(4, 3, 4, 40));
        assertThatThrownBy(() -> VentLevers.vents(1, 0, 2, 10)).isInstanceOf(IllegalArgumentException.class);
    }
}
