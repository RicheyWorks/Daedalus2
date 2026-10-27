// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SignalTreeTest {

    /** Brute force: try every parent choice for every non-flagship ship, keep acyclic ones. */
    private static long brute(int n, int root, long[][] links) {
        long[][] w = new long[n][n];
        for (long[] row : w) {
            Arrays.fill(row, Long.MAX_VALUE);
        }
        for (long[] e : links) {
            int u = (int) e[0];
            int v = (int) e[1];
            if (u != v) {
                w[u][v] = Math.min(w[u][v], e[2]);
            }
        }
        int[] par = new int[n];
        long best = Long.MAX_VALUE;
        int combos = 1;
        for (int i = 0; i < n - 1; i++) {
            combos *= n;
        }
        for (int c = 0; c < combos; c++) {
            int x = c;
            long sum = 0;
            boolean ok = true;
            for (int v = 0; v < n && ok; v++) {
                if (v == root) {
                    continue;
                }
                par[v] = x % n;
                x /= n;
                if (w[par[v]][v] == Long.MAX_VALUE) {
                    ok = false;
                } else {
                    sum += w[par[v]][v];
                }
            }
            for (int v = 0; v < n && ok; v++) {
                int y = v;
                for (int s = 0; s <= n && y != root; s++) {
                    y = par[y];
                }
                ok = y == root;
            }
            if (ok) {
                best = Math.min(best, sum);
            }
        }
        return best == Long.MAX_VALUE ? -1 : best;
    }

    private static long[][] randomLinks(SplittableRandom r, int n, int m, int maxCost) {
        long[][] e = new long[m][];
        for (int i = 0; i < m; i++) {
            e[i] = new long[] {r.nextInt(n), r.nextInt(n), r.nextInt(maxCost + 1)};
        }
        return e;
    }

    @Test
    void handBuiltCycleIsContracted() {
        long[][] links = {{0, 1, 10}, {1, 2, 1}, {2, 1, 1}, {0, 2, 12}, {2, 3, 2}};
        assertThat(SignalTree.cost(4, 0, links)).isEqualTo(brute(4, 0, links)).isEqualTo(13);
        assertThat(SignalTree.quest(4, 0, links, 13)).isTrue();
        assertThat(SignalTree.quest(4, 0, links, 12)).isFalse();
    }

    @Test
    void randomFleetsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(449);
        for (int it = 0; it < 400; it++) {
            int n = 1 + r.nextInt(6);
            int root = r.nextInt(n);
            long[][] links = randomLinks(r, n, r.nextInt(3 * n + 1), 1 + r.nextInt(20));
            assertThat(SignalTree.cost(n, root, links)).isEqualTo(brute(n, root, links));
        }
    }

    @Test
    void unreachableShipGivesMinusOne() {
        long[][] links = {{0, 1, 3}, {2, 1, 1}};
        assertThat(SignalTree.cost(3, 0, links)).isEqualTo(-1);
        assertThat(SignalTree.cost(1, 0, new long[0][])).isZero();
    }

    @Test
    void largestFleetMatchesChainBound() {
        SplittableRandom r = new SplittableRandom(7);
        int n = SignalTree.MAX_SHIPS;
        long[][] links = new long[SignalTree.MAX_LINKS][];
        for (int i = 0; i < n - 1; i++) {
            links[i] = new long[] {i, i + 1, 1};
        }
        for (int i = n - 1; i < links.length; i++) {
            links[i] = new long[] {r.nextInt(n), r.nextInt(n), 1 + r.nextInt(1_000_000_000)};
        }
        long c = SignalTree.cost(n, 0, links);
        assertThat(c).isBetween(0L, (long) n - 1);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> SignalTree.cost(0, 0, new long[0][]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalTree.cost(3, 3, new long[0][]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalTree.cost(3, 0, new long[][] {{0, 5, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalTree.cost(3, 0, new long[][] {{0, 1, -1}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}