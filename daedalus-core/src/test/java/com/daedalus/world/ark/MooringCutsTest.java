// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class MooringCutsTest {

    /** Brute force: smallest cut over every island subset holding u but not v. */
    private static long bruteCut(int n, int[][] lines, int u, int v) {
        long best = Long.MAX_VALUE;
        for (int mask = 0; mask < 1 << n; mask++) {
            if ((mask >> u & 1) == 1 && (mask >> v & 1) == 0) {
                long c = 0;
                for (int[] l : lines) {
                    if ((mask >> l[0] & 1) != (mask >> l[1] & 1)) {
                        c += l[2];
                    }
                }
                best = Math.min(best, c);
            }
        }
        return best;
    }

    private static int[][] randomLines(SplittableRandom rnd, int n, int count) {
        List<int[]> out = new ArrayList<>();
        for (int k = 0; k < count; k++) {
            out.add(new int[] {rnd.nextInt(n), rnd.nextInt(n), rnd.nextInt(10)});
        }
        return out.toArray(new int[0][]);
    }

    @Test
    void everyPairMatchesBruteForceOnRandomFlotillas() {
        SplittableRandom rnd = new SplittableRandom(510L);
        for (int trial = 0; trial < 60; trial++) {
            int n = 2 + rnd.nextInt(7);
            int[][] lines = randomLines(rnd, n, rnd.nextInt(3 * n));
            MooringCuts mc = new MooringCuts(n, lines);
            for (int u = 0; u < n; u++) {
                for (int v = 0; v < n; v++) {
                    if (u != v) {
                        assertThat(mc.minCut(u, v)).as("trial %d %d-%d", trial, u, v)
                            .isEqualTo(bruteCut(n, lines, u, v));
                    }
                }
            }
        }
    }

    @Test
    void treeHasNMinusOneEdgesAndWeakestPairIsTheSmallestCut() {
        SplittableRandom rnd = new SplittableRandom(7L);
        for (int trial = 0; trial < 20; trial++) {
            int n = 3 + rnd.nextInt(5);
            int[][] lines = randomLines(rnd, n, 2 * n);
            MooringCuts mc = new MooringCuts(n, lines);
            int[] p = mc.parents();
            assertThat(p[0]).isZero();
            long smallest = Long.MAX_VALUE;
            for (int u = 0; u < n; u++) {
                for (int v = u + 1; v < n; v++) {
                    smallest = Math.min(smallest, bruteCut(n, lines, u, v));
                }
            }
            assertThat(mc.weakestPair()[2]).isEqualTo(smallest);
            long minEdge = Long.MAX_VALUE;
            long[] w = mc.weights();
            for (int i = 1; i < n; i++) {
                minEdge = Math.min(minEdge, w[i]);
            }
            assertThat(minEdge).isEqualTo(smallest);
        }
    }

    @Test
    void handWorkedFlotillaAndChart() {
        int[][] lines = {{0, 1, 3}, {1, 2, 2}, {0, 2, 1}, {2, 3, 4}, {3, 3, 9}};
        MooringCuts mc = new MooringCuts(4, lines);
        assertThat(mc.minCut(0, 1)).isEqualTo(4);
        assertThat(mc.minCut(1, 2)).isEqualTo(3);
        assertThat(mc.minCut(2, 3)).isEqualTo(4);
        assertThat(mc.minCut(0, 3)).isEqualTo(3);
        assertThat(mc.islands()).isEqualTo(4);
        assertThat(mc.chart()).contains("4 islands").contains("strength 3");
        assertThat(new MooringCuts(1, new int[0][]).chart()).contains("lone island");
        MooringCuts apart = new MooringCuts(3, new int[][] {{0, 1, 5}});
        assertThat(apart.minCut(0, 2)).isZero();
        assertThat(apart.minCut(0, 1)).isEqualTo(5);
    }

    @Test
    void questAndBadInput() {
        int[][] lines = {{0, 1, 3}, {1, 2, 2}, {0, 2, 1}};
        assertThat(MooringCuts.QUEST_ID).isEqualTo("q_mooring_cuts");
        assertThat(MooringCuts.quest(3, lines, 0, 2, 3)).isTrue();
        assertThat(MooringCuts.quest(3, lines, 0, 2, 2)).isFalse();
        assertThatThrownBy(() -> new MooringCuts(0, lines)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new MooringCuts(2, new int[][] {{0, 2, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new MooringCuts(2, new int[][] {{0, 1, -1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new MooringCuts(3, lines).minCut(1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new MooringCuts(1, new int[0][]).weakestPair())
            .isInstanceOf(IllegalStateException.class);
    }
}