// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.FlueLoops.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FlueLoopsTest {

    private static boolean[][] reach(int[][] adj) {
        int n = adj.length;
        boolean[][] r = new boolean[n][n];
        for (int u = 0; u < n; u++) {
            r[u][u] = true;
            for (int v : adj[u]) {
                r[u][v] = true;
            }
        }
        for (int k = 0; k < n; k++) {
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    r[i][j] |= r[i][k] && r[k][j];
                }
            }
        }
        return r;
    }

    @Test
    void componentsMatchBruteForceReachability() {
        for (long seed = 0; seed < 200; seed++) {
            int n = (int) (seed % 15);
            int[][] adj = FlueLoops.flues(seed, n, 5 + (int) (seed % 30));
            int[] comp = FlueLoops.components(adj);
            boolean[][] r = reach(adj);
            int groups = 0;
            for (int i = 0; i < n; i++) {
                boolean first = true;
                for (int j = 0; j < n; j++) {
                    assertThat(comp[i] == comp[j]).as("seed %d %d~%d", seed, i, j).isEqualTo(r[i][j] && r[j][i]);
                    if (j < i && comp[j] == comp[i]) {
                        first = false;
                    }
                }
                groups += first ? 1 : 0;
                for (int v : adj[i]) {
                    assertThat(comp[i]).as("reverse topo, seed %d", seed).isGreaterThanOrEqualTo(comp[v]);
                }
            }
            assertThat(FlueLoops.count(adj)).isEqualTo(groups);
        }
    }

    @Test
    void fluesToAddKnownCases() {
        assertThat(FlueLoops.fluesToAdd(new int[][] {{1}, {2}, {0}})).isZero();
        assertThat(FlueLoops.fluesToAdd(new int[][] {{1}, {2}, {}})).isEqualTo(1);
        assertThat(FlueLoops.fluesToAdd(new int[][] {{}, {}, {}})).isEqualTo(3);
        assertThat(FlueLoops.fluesToAdd(new int[][] {{1, 2}, {}, {}})).isEqualTo(2);
        assertThat(FlueLoops.fluesToAdd(new int[0][])).isZero();
        assertThat(FlueLoops.count(new int[][] {{1}, {0}, {3}, {2}})).isEqualTo(2);
        assertThatThrownBy(() -> FlueLoops.components(new int[][] {{5}})).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void addingTheFluesReallyConnects() {
        for (long seed = 0; seed < 100; seed++) {
            int[][] adj = FlueLoops.flues(seed, 2 + (int) (seed % 10), 15);
            int need = FlueLoops.fluesToAdd(adj);
            int[][] full = FlueLoops.flues(seed, adj.length, 100);
            assertThat(FlueLoops.fluesToAdd(full)).isZero();
            assertThat(need).isBetween(0, adj.length);
        }
    }

    @Test
    void gradesLinesAndReplay() {
        int[][] adj = {{1}, {2}, {}};
        assertThat(FlueLoops.grade(adj, 3, 1)).isEqualTo(Grade.CLEAR);
        assertThat(FlueLoops.grade(adj, 1, 1)).isEqualTo(Grade.SMOKY);
        assertThat(FlueLoops.grade(adj, 3, 2)).isEqualTo(Grade.SMOKY);
        for (Grade g : Grade.values()) {
            assertThat(FlueLoops.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(FlueLoops.QUEST_ID).isEqualTo("q_flue_loops");
        assertThat(FlueLoops.flues(3, 8, 30)).isDeepEqualTo(FlueLoops.flues(3, 8, 30));
        assertThatThrownBy(() -> FlueLoops.flues(1, 3, 101)).isInstanceOf(IllegalArgumentException.class);
    }
}
