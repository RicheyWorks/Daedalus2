// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BulkheadChokesTest {

    /** Reachable set from root with room 'cut' sealed (-1 for none). */
    private static boolean[] reach(int n, int root, int[][] e, int cut) {
        boolean[] r = new boolean[n];
        if (root == cut) {
            return r;
        }
        r[root] = true;
        boolean grew = true;
        while (grew) {
            grew = false;
            for (int[] x : e) {
                if (r[x[0]] && !r[x[1]] && x[1] != cut) {
                    r[x[1]] = true;
                    grew = true;
                }
            }
        }
        return r;
    }

    /** Brute force: strict dominator sets, then the idom is the strict dominator with most dominators. */
    private static int[] brute(int n, int root, int[][] e) {
        boolean[] base = reach(n, root, e, -1);
        boolean[][] dom = new boolean[n][n];
        for (int d = 0; d < n; d++) {
            boolean[] r = reach(n, root, e, d);
            for (int v = 0; v < n; v++) {
                dom[d][v] = base[v] && base[d] && !r[v];
            }
        }
        int[] id = new int[n];
        for (int v = 0; v < n; v++) {
            if (!base[v]) {
                id[v] = -1;
                continue;
            }
            if (v == root) {
                id[v] = root;
                continue;
            }
            int best = -1;
            int bestCount = -1;
            for (int d = 0; d < n; d++) {
                if (d != v && dom[d][v]) {
                    int c = 0;
                    for (int k = 0; k < n; k++) {
                        if (dom[k][d]) {
                            c++;
                        }
                    }
                    if (c > bestCount) {
                        bestCount = c;
                        best = d;
                    }
                }
            }
            id[v] = best;
        }
        return id;
    }

    @Test
    void diamondAndChain() {
        int[][] e = {{0, 1}, {0, 2}, {1, 3}, {2, 3}, {3, 4}};
        assertThat(BulkheadChokes.idom(5, 0, e)).containsExactly(0, 0, 0, 0, 3);
        assertThat(BulkheadChokes.chokes(5, 0, e, 4)).isEqualTo(1);
        assertThat(BulkheadChokes.quest(5, 0, e, 4, 1)).isTrue();
        assertThat(BulkheadChokes.quest(5, 0, e, 3, 1)).isFalse();
    }

    @Test
    void randomShipsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(458);
        for (int it = 0; it < 1500; it++) {
            int n = 1 + r.nextInt(9);
            int[][] e = new int[r.nextInt(3 * n + 1)][];
            for (int i = 0; i < e.length; i++) {
                e[i] = new int[] {r.nextInt(n), r.nextInt(n)};
            }
            int root = r.nextInt(n);
            assertThat(BulkheadChokes.idom(n, root, e)).containsExactly(brute(n, root, e));
        }
    }

    @Test
    void unreachableRoomsAndSelfLoops() {
        int[][] e = {{0, 0}, {1, 2}};
        assertThat(BulkheadChokes.idom(3, 0, e)).containsExactly(0, -1, -1);
        assertThat(BulkheadChokes.chokes(3, 0, e, 2)).isEqualTo(-1);
    }

    @Test
    void largestShipLongChain() {
        int n = BulkheadChokes.MAX_ROOMS;
        int[][] e = new int[n - 1][];
        for (int i = 0; i + 1 < n; i++) {
            e[i] = new int[] {i, i + 1};
        }
        assertThat(BulkheadChokes.chokes(n, 0, e, n - 1)).isEqualTo(n - 2);
        SplittableRandom r = new SplittableRandom(9);
        int[][] g = new int[BulkheadChokes.MAX_PASSAGES][];
        for (int i = 0; i < g.length; i++) {
            g[i] = new int[] {r.nextInt(n), r.nextInt(n)};
        }
        int[] d = BulkheadChokes.idom(n, 0, g);
        assertThat(d[0]).isZero();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> BulkheadChokes.idom(0, 0, new int[0][]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BulkheadChokes.idom(3, 0, new int[][] {{0, 3}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BulkheadChokes.chokes(3, 0, new int[0][], 5))
            .isInstanceOf(IllegalArgumentException.class);
    }
}