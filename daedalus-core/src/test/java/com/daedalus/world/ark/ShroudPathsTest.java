// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ShroudPathsTest {

    /** Brute force: spars on the a-b path by walking parent pointers from a plain BFS. */
    private static List<Integer> walk(int n, int[][] lines, int a, int b) {
        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            adj.add(new ArrayList<>());
        }
        for (int[] l : lines) {
            adj.get(l[0]).add(l[1]);
            adj.get(l[1]).add(l[0]);
        }
        int[] par = new int[n];
        Arrays.fill(par, -2);
        par[a] = -1;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        q.add(a);
        while (!q.isEmpty()) {
            int v = q.poll();
            for (int w : adj.get(v)) {
                if (par[w] == -2) {
                    par[w] = v;
                    q.add(w);
                }
            }
        }
        List<Integer> out = new ArrayList<>();
        for (int v = b; v != -1; v = par[v]) {
            out.add(v);
        }
        return out;
    }

    private static int[][] randomTree(int n, SplittableRandom rnd, boolean chainy) {
        int[][] lines = new int[n - 1][];
        for (int v = 1; v < n; v++) {
            int p = chainy ? Math.max(0, v - 1 - rnd.nextInt(2)) : rnd.nextInt(v);
            lines[v - 1] = rnd.nextBoolean() ? new int[] {p, v} : new int[] {v, p};
        }
        return lines;
    }

    @Test
    void pathQueriesMatchBruteForceWithUpdates() {
        SplittableRandom rnd = new SplittableRandom(520);
        for (int trial = 0; trial < 60; trial++) {
            int n = 1 + rnd.nextInt(40);
            int[][] lines = randomTree(n, rnd, (trial & 1) != 0);
            long[] strain = new long[n];
            for (int v = 0; v < n; v++) {
                strain[v] = rnd.nextLong(-1000, 1000);
            }
            ShroudPaths sp = new ShroudPaths(n, lines, strain);
            for (int qq = 0; qq < 80; qq++) {
                if (rnd.nextInt(4) == 0) {
                    int v = rnd.nextInt(n);
                    strain[v] = rnd.nextLong(-1000, 1000);
                    sp.set(v, strain[v]);
                    assertThat(sp.strain(v)).isEqualTo(strain[v]);
                    continue;
                }
                int a = rnd.nextInt(n);
                int b = rnd.nextInt(n);
                List<Integer> path = walk(n, lines, a, b);
                long m = Long.MIN_VALUE;
                long t = 0;
                for (int v : path) {
                    m = Math.max(m, strain[v]);
                    t += strain[v];
                }
                assertThat(sp.pathMax(a, b)).isEqualTo(m);
                assertThat(sp.pathSum(a, b)).isEqualTo(t);
                assertThat(sp.pathLength(a, b)).isEqualTo(path.size());
                assertThat(path).contains(sp.meet(a, b));
            }
        }
    }

    @Test
    void meetIsTheLowestCommonAncestorByBruteForce() {
        SplittableRandom rnd = new SplittableRandom(7);
        int n = 30;
        int[][] lines = randomTree(n, rnd, false);
        ShroudPaths sp = new ShroudPaths(n, lines, new long[n]);
        for (int a = 0; a < n; a++) {
            for (int b = 0; b < n; b++) {
                List<Integer> fromA = walk(n, lines, 0, a);
                List<Integer> fromB = walk(n, lines, 0, b);
                int best = 0;
                for (int v : fromA) {
                    if (fromB.contains(v)) {
                        best = v;
                        break;
                    }
                }
                assertThat(sp.meet(a, b)).as("%d %d", a, b).isEqualTo(best);
            }
        }
    }

    @Test
    void longChainStaysFastAndQuestChecksTheMax() {
        int n = 200_000;
        int[][] lines = new int[n - 1][];
        long[] strain = new long[n];
        for (int v = 1; v < n; v++) {
            lines[v - 1] = new int[] {v - 1, v};
            strain[v] = v;
        }
        ShroudPaths sp = new ShroudPaths(n, lines, strain);
        assertThat(sp.pathMax(0, n - 1)).isEqualTo(n - 1L);
        assertThat(sp.pathSum(0, n - 1)).isEqualTo((long) n * (n - 1) / 2);
        sp.set(5, 1_000_000L);
        assertThat(sp.pathMax(3, 9)).isEqualTo(1_000_000L);
        assertThat(ShroudPaths.quest(sp, 3, 9, 1_000_000L)).isTrue();
        assertThat(ShroudPaths.quest(sp, 3, 9, 9L)).isFalse();
        assertThat(ShroudPaths.quest(null, 0, 0, 0L)).isFalse();
    }

    @Test
    void rejectsBadRiggings() {
        assertThatThrownBy(() -> new ShroudPaths(3, new int[][] {{0, 1}, {0, 1}}, new long[3]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ShroudPaths(2, new int[][] {{0, 0}}, new long[2]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ShroudPaths(2, new int[][] {{0, 1}}, new long[1]))
            .isInstanceOf(IllegalArgumentException.class);
        ShroudPaths one = new ShroudPaths(1, new int[0][], new long[] {42});
        assertThat(one.pathMax(0, 0)).isEqualTo(42);
        assertThatThrownBy(() -> one.strain(1)).isInstanceOf(IllegalArgumentException.class);
    }
}
