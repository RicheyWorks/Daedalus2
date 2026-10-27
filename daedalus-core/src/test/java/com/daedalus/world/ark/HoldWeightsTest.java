// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class HoldWeightsTest {

    private static final int[] NONE = new int[9];

    private static int[] cluesOf(int[] b) {
        return new int[] {b[0] + b[1] + b[3] + b[4], b[1] + b[2] + b[4] + b[5],
            b[3] + b[4] + b[6] + b[7], b[4] + b[5] + b[7] + b[8]};
    }

    private static String key(int[] c) {
        return c[0] + "," + c[1] + "," + c[2] + "," + c[3];
    }

    /** Every permutation of 1..9, tallied by its clue set. */
    private static Map<String, Long> tally() {
        Map<String, Long> m = new HashMap<>();
        int[] p = {1, 2, 3, 4, 5, 6, 7, 8, 9};
        int[] c = new int[9];
        m.merge(key(cluesOf(p)), 1L, Long::sum);
        int i = 0;
        while (i < 9) {
            if (c[i] < i) {
                int j = (i & 1) == 0 ? 0 : c[i];
                int x = p[j];
                p[j] = p[i];
                p[i] = x;
                m.merge(key(cluesOf(p)), 1L, Long::sum);
                c[i]++;
                i = 0;
            } else {
                c[i] = 0;
                i++;
            }
        }
        return m;
    }

    @Test
    void countsMatchBruteForceOverAllFillings() {
        Map<String, Long> m = tally();
        long total = 0;
        for (long v : m.values()) {
            total += v;
        }
        assertThat(total).isEqualTo(362880L);
        SplittableRandom rnd = new SplittableRandom(402);
        String[] keys = m.keySet().toArray(new String[0]);
        Arrays.sort(keys);
        for (int t = 0; t < 40; t++) {
            String k = keys[rnd.nextInt(keys.length)];
            String[] parts = k.split(",");
            int[] cl = new int[4];
            for (int j = 0; j < 4; j++) {
                cl[j] = Integer.parseInt(parts[j]);
            }
            assertThat(HoldWeights.count(cl, NONE, Long.MAX_VALUE)).as(k).isEqualTo(m.get(k));
        }
        int[] impossible = {10, 10, 10, 10};
        assertThat(m.get(key(impossible))).isNull();
        assertThat(HoldWeights.count(impossible, NONE, Long.MAX_VALUE)).isZero();
        assertThat(HoldWeights.solve(impossible, NONE)).isEmpty();
    }

    @Test
    void givensNarrowToOne() {
        int[] hidden = {4, 9, 2, 3, 5, 7, 8, 1, 6};
        int[] cl = cluesOf(hidden);
        int[] g = hidden.clone();
        g[0] = 0;
        g[8] = 0;
        assertThat(HoldWeights.count(cl, g, Long.MAX_VALUE)).isEqualTo(1);
        assertThat(HoldWeights.solve(cl, g)).containsExactly(hidden);
    }

    @Test
    void solveAndQuest() {
        int[] cl = cluesOf(new int[] {2, 7, 6, 9, 5, 1, 4, 3, 8});
        int[] s = HoldWeights.solve(cl, NONE);
        assertThat(s).hasSize(9);
        assertThat(HoldWeights.quest(cl, NONE, s)).isTrue();
        int[] bad = s.clone();
        bad[0] = bad[1];
        assertThat(HoldWeights.quest(cl, NONE, bad)).isFalse();
        assertThat(HoldWeights.QUEST_ID).isEqualTo("q_hold_weights");
        assertThatThrownBy(() -> HoldWeights.count(new int[3], NONE, 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}