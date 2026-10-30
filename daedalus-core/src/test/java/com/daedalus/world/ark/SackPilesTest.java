// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class SackPilesTest {

    /** Brute walk with a list of visited layouts compared by value. */
    private static int[] bruteRho(int[] p) {
        List<List<Integer>> seen = new ArrayList<>();
        List<Integer> cur = new ArrayList<>();
        for (int v : p) {
            cur.add(v);
        }
        while (!seen.contains(cur)) {
            seen.add(cur);
            List<Integer> nx = new ArrayList<>();
            nx.add(cur.size());
            for (int v : cur) {
                if (v > 1) {
                    nx.add(v - 1);
                }
            }
            nx.sort((a, b) -> b - a);
            cur = nx;
        }
        int first = seen.indexOf(cur);
        return new int[] {first, seen.size() - first};
    }

    @Test
    void matchesBruteWalk() {
        for (int n = 1; n <= 21; n++) {
            for (int[] p : SackPiles.partitions(n)) {
                int[] b = bruteRho(p);
                assertThat(SackPiles.tail(p)).as("%s", Arrays.toString(p)).isEqualTo(b[0]);
                assertThat(SackPiles.cycleLength(p)).isEqualTo(b[1]);
            }
        }
        assertThat(SackPiles.partitions(10)).hasSize(42);
    }

    @Test
    void triangularSettlesOnStaircase() {
        for (int k = 1; k <= 6; k++) {
            int n = k * (k + 1) / 2;
            int[] stair = new int[k];
            for (int i = 0; i < k; i++) {
                stair[i] = k - i;
            }
            for (int[] p : SackPiles.partitions(n)) {
                int[][] c = SackPiles.cycle(p);
                assertThat(c.length).isEqualTo(1);
                assertThat(c[0]).containsExactly(stair);
            }
            assertThat(SackPiles.worstTail(n)).isLessThanOrEqualTo(k * k - k);
        }
    }

    @Test
    void cycleMembersStayInTheCycle() {
        for (int[] p : SackPiles.partitions(17)) {
            int[][] c = SackPiles.cycle(p);
            for (int i = 0; i < c.length; i++) {
                assertThat(SackPiles.step(c[i])).containsExactly(c[(i + 1) % c.length]);
                assertThat(SackPiles.tail(c[i])).isZero();
            }
        }
    }

    @Test
    void questAndBounds() {
        int[] p = {5};
        int t = bruteRho(p)[0];
        assertThat(SackPiles.quest(p, t)).isTrue();
        assertThat(SackPiles.quest(p, t + 1)).isFalse();
        assertThat(SackPiles.step(new int[] {3, 1})).containsExactly(2, 2);
        assertThat(SackPiles.QUEST_ID).isEqualTo("q_sack_piles");
        assertThat(SackPiles.tail(new int[] {60})).isGreaterThan(0);
        assertThatThrownBy(() -> SackPiles.step(new int[] {1, 2})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SackPiles.step(new int[] {61})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SackPiles.partitions(31)).isInstanceOf(IllegalArgumentException.class);
    }
}