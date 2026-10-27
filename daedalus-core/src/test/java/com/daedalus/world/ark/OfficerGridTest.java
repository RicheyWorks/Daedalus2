// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class OfficerGridTest {

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
        for (int v = 0; v < n; v++) {
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

    private static boolean bruteExists(int n) {
        List<int[][]> all = new ArrayList<>();
        latins(n, new int[n][n], 0, all);
        for (int[][] a : all) {
            for (int[][] b : all) {
                if (OfficerGrid.isGraecoLatin(a, b)) {
                    return true;
                }
            }
        }
        return false;
    }

    @Test
    void smallOrdersMatchBruteForce() {
        for (int n = 1; n <= 4; n++) {
            boolean want = bruteExists(n);
            assertThat(want).isEqualTo(n != 2);
            assertThat(OfficerGrid.build(n).length > 0).isEqualTo(want);
        }
    }

    @Test
    void builtGridsAreValid() {
        int built = 0;
        for (int n = 1; n <= 200; n++) {
            int[][][] g = OfficerGrid.build(n);
            if (g.length > 0) {
                built++;
                assertThat(OfficerGrid.isGraecoLatin(g[0], g[1])).isTrue();
                assertThat(g[0].length).isEqualTo(n);
            }
        }
        assertThat(built).isGreaterThan(100);
        assertThat(OfficerGrid.build(6)).isEmpty();
    }

    @Test
    void questAndGuards() {
        assertThat(OfficerGrid.QUEST_ID).isEqualTo("q_officer_grid");
        int[][][] g = OfficerGrid.build(3);
        assertThat(OfficerGrid.quest(3, g[0], g[1])).isTrue();
        assertThat(OfficerGrid.quest(3, g[0], g[0])).isFalse();
        assertThatThrownBy(() -> OfficerGrid.build(201)).isInstanceOf(IllegalArgumentException.class);
    }
}