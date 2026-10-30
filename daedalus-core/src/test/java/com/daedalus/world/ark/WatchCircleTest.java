// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class WatchCircleTest {

    @Test
    void orderAndSurvivorMatchDirectSimulation() {
        for (int n = 1; n <= 60; n++) {
            for (int k = 1; k <= 12; k++) {
                int[] sim = simulate(n, k);
                assertThat(WatchCircle.order(n, k)).as("n=%d k=%d", n, k).containsExactly(sim);
                assertThat(WatchCircle.survivor(n, k)).isEqualTo(sim[n - 1]);
            }
        }
    }

    @Test
    void classicValues() {
        assertThat(WatchCircle.order(7, 3)).containsExactly(3, 6, 2, 7, 5, 1, 4);
        assertThat(WatchCircle.survivor(41, 3)).isEqualTo(31);
        assertThat(WatchCircle.survivor(10, 1)).isEqualTo(10);
        for (int n = 1; n <= 64; n++) {
            int l = n - Integer.highestOneBit(n);
            assertThat(WatchCircle.survivor(n, 2)).isEqualTo(2 * l + 1);
        }
    }

    @Test
    void largeCrewsAndBigSteps() {
        int[] o = WatchCircle.order(100_000, 7);
        assertThat(o[o.length - 1]).isEqualTo(WatchCircle.survivor(100_000, 7));
        assertThat(WatchCircle.survivor(5, Integer.MAX_VALUE)).isEqualTo(simulate(5, Integer.MAX_VALUE)[4]);
        boolean[] seen = new boolean[100_001];
        for (int s : o) {
            assertThat(seen[s]).isFalse();
            seen[s] = true;
        }
    }

    @Test
    void questAndValidation() {
        assertThat(WatchCircle.quest(7, 3, 4)).isTrue();
        assertThat(WatchCircle.quest(7, 3, 1)).isFalse();
        assertThat(WatchCircle.QUEST_ID).isEqualTo("q_watch_circle");
        assertThatThrownBy(() -> WatchCircle.survivor(0, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WatchCircle.order(3, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int[] simulate(int n, int k) {
        List<Integer> ring = new ArrayList<>();
        for (int i = 1; i <= n; i++) {
            ring.add(i);
        }
        int[] out = new int[n];
        long idx = 0;
        for (int t = 0; t < n; t++) {
            idx = (idx + k - 1) % ring.size();
            out[t] = ring.remove((int) idx);
        }
        return out;
    }
}
