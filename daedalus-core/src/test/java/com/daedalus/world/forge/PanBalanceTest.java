// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.PanBalance.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class PanBalanceTest {

    @Test
    void matchesBruteForceOnSeededHeaps() {
        for (long seed = 0; seed < 250; seed++) {
            int n = (int) (seed % 13);
            int[] w = PanBalance.ingots(seed, n, 1 + (int) (seed % 40));
            int total = 0;
            for (int x : w) {
                total += x;
            }
            boolean[] sums = new boolean[total + 1];
            int best = Integer.MAX_VALUE;
            for (int mask = 0; mask < (1 << n); mask++) {
                int s = 0;
                for (int i = 0; i < n; i++) {
                    if (((mask >> i) & 1) == 1) {
                        s += w[i];
                    }
                }
                sums[s] = true;
                best = Math.min(best, Math.abs(total - 2 * s));
            }
            boolean[] left = PanBalance.bestSplit(w);
            assertThat(PanBalance.imbalance(w, left)).as("seed %d", seed).isEqualTo(best);
            assertThat(PanBalance.grade(w, left)).isEqualTo(Grade.LEVEL);
            for (int t = 0; t <= total; t++) {
                assertThat(PanBalance.reachable(w, t)).as("seed %d t %d", seed, t).isEqualTo(sums[t]);
            }
            assertThat(PanBalance.reachable(w, total + 1)).isFalse();
        }
    }

    @Test
    void knownHeaps() {
        int[] w = {3, 1, 4, 2, 2};
        assertThat(PanBalance.imbalance(w, PanBalance.bestSplit(w))).isZero();
        assertThat(PanBalance.imbalance(new int[] {10, 1}, PanBalance.bestSplit(new int[] {10, 1}))).isEqualTo(9);
        assertThat(PanBalance.bestSplit(new int[0])).isEmpty();
        assertThat(PanBalance.reachable(new int[] {5, 7}, 12)).isTrue();
        assertThat(PanBalance.reachable(new int[] {5, 7}, 6)).isFalse();
        assertThatThrownBy(() -> PanBalance.reachable(new int[] {-1}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PanBalance.bestSplit(new int[] {PanBalance.MAX_TOTAL, 1}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[] w = {3, 1, 4, 2, 2};
        assertThat(PanBalance.grade(w, new boolean[] {true, true, false, true, false})).isEqualTo(Grade.LEVEL);
        assertThat(PanBalance.grade(w, new boolean[] {true, false, false, false, false})).isEqualTo(Grade.TILTED);
        assertThat(PanBalance.grade(w, new boolean[2])).isEqualTo(Grade.TILTED);
        for (Grade g : Grade.values()) {
            assertThat(PanBalance.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PanBalance.QUEST_ID).isEqualTo("q_pan_balance");
        assertThat(PanBalance.ingots(4, 6, 9)).containsExactly(PanBalance.ingots(4, 6, 9));
        assertThatThrownBy(() -> PanBalance.ingots(1, 2, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
