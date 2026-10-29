// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.CoalHeaps.Grade;
import com.daedalus.world.forge.CoalHeaps.Move;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CoalHeapsTest {

    private static boolean wins(int[] h, int[] take, Map<String, Boolean> memo) {
        int[] key = h.clone();
        Arrays.sort(key);
        String k = Arrays.toString(key);
        Boolean c = memo.get(k);
        if (c != null) {
            return c;
        }
        boolean w = false;
        for (int i = 0; i < h.length && !w; i++) {
            for (int t : take) {
                if (t <= h[i]) {
                    h[i] -= t;
                    boolean opp = wins(h, take, memo);
                    h[i] += t;
                    if (!opp) {
                        w = true;
                        break;
                    }
                }
            }
        }
        memo.put(k, w);
        return w;
    }

    @Test
    void matchesMinimaxOnSeededPositions() {
        int[][] sets = {{1, 2, 3}, {1, 3, 4}, {2, 5}, {1}, {1, 4, 9}};
        for (long seed = 0; seed < 150; seed++) {
            int[] take = sets[(int) (seed % sets.length)];
            int[] h = CoalHeaps.heaps(seed, 1 + (int) (seed % 3), 12);
            boolean truth = wins(h.clone(), take, new HashMap<>());
            assertThat(CoalHeaps.nimSum(h, take) != 0).as("seed %d", seed).isEqualTo(truth);
            Move m = CoalHeaps.winningMove(h, take);
            if (truth) {
                assertThat(m).isNotNull();
                int[] after = h.clone();
                after[m.heap()] -= m.amount();
                assertThat(wins(after, take, new HashMap<>())).as("seed %d after", seed).isFalse();
                assertThat(CoalHeaps.grade(h, take, m)).isEqualTo(Grade.STOKED);
            } else {
                assertThat(m).isNull();
                assertThat(CoalHeaps.grade(h, take, null)).isEqualTo(Grade.STOKED);
            }
        }
    }

    @Test
    void knownTables() {
        assertThat(CoalHeaps.grundyTable(new int[] {1, 2, 3}, 8)).containsExactly(0, 1, 2, 3, 0, 1, 2, 3, 0);
        assertThat(CoalHeaps.nimSum(new int[] {4, 8}, new int[] {1, 2, 3})).isZero();
        assertThat(CoalHeaps.winningMove(new int[] {5}, new int[] {1, 2, 3})).isEqualTo(new Move(0, 1));
        assertThatThrownBy(() -> CoalHeaps.grundyTable(new int[] {0}, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CoalHeaps.nimSum(new int[] {-1}, new int[] {1}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[] take = {1, 2, 3};
        assertThat(CoalHeaps.grade(new int[] {5}, take, new Move(0, 2))).isEqualTo(Grade.SMOTHERED);
        assertThat(CoalHeaps.grade(new int[] {5}, take, null)).isEqualTo(Grade.SMOTHERED);
        assertThat(CoalHeaps.grade(new int[] {5}, take, new Move(0, 4))).isEqualTo(Grade.SMOTHERED);
        assertThat(CoalHeaps.grade(new int[] {4}, take, new Move(0, 1))).isEqualTo(Grade.SMOTHERED);
        for (Grade g : Grade.values()) {
            assertThat(CoalHeaps.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(CoalHeaps.QUEST_ID).isEqualTo("q_coal_heaps");
        assertThat(CoalHeaps.heaps(3, 4, 9)).containsExactly(CoalHeaps.heaps(3, 4, 9));
        assertThatThrownBy(() -> CoalHeaps.heaps(1, 0, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
