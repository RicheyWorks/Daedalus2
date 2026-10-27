// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class WatchGridTest {

    private static void perms(int[] a, int k, List<int[]> out) {
        if (k == a.length) {
            out.add(a.clone());
            return;
        }
        for (int i = k; i < a.length; i++) {
            int x = a[k];
            a[k] = a[i];
            a[i] = x;
            perms(a, k + 1, out);
            a[i] = a[k];
            a[k] = x;
        }
    }

    private static long brute(int n, List<int[]> ps, int[][] g, int row) {
        if (row == n) {
            return WatchGrid.isFair(g) ? 1 : 0;
        }
        long t = 0;
        for (int[] p : ps) {
            g[row] = p;
            t += brute(n, ps, g, row + 1);
        }
        return t;
    }

    @Test
    void countMatchesBruteForceRowPermutations() {
        for (int n = 1; n <= 4; n++) {
            int[] id = new int[n];
            for (int i = 0; i < n; i++) {
                id[i] = i;
            }
            List<int[]> ps = new ArrayList<>();
            perms(id, 0, ps);
            assertThat(WatchGrid.count(n)).isEqualTo(brute(n, ps, new int[n][], 0));
        }
        assertThat(WatchGrid.count(5)).isEqualTo(161_280L);
    }

    @Test
    void cyclicIsFair() {
        for (int n = 1; n <= 40; n++) {
            assertThat(WatchGrid.isFair(WatchGrid.cyclic(n))).isTrue();
        }
    }

    @Test
    void questAndGuards() {
        assertThat(WatchGrid.QUEST_ID).isEqualTo("q_watch_grid");
        assertThat(WatchGrid.quest(2, new int[][] {{0, 1}, {1, 0}})).isTrue();
        assertThat(WatchGrid.quest(2, new int[][] {{0, 1}, {0, 1}})).isFalse();
        assertThat(WatchGrid.isFair(new int[][] {{0, 1}, {1}})).isFalse();
        assertThatThrownBy(() -> WatchGrid.count(6)).isInstanceOf(IllegalArgumentException.class);
    }
}