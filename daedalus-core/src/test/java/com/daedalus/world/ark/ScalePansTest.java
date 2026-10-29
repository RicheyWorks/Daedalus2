// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ScalePansTest {

    @Test
    void uniqueBalanceMatchesBruteForce() {
        int k = 7;
        Map<Long, int[]> seen = new HashMap<>();
        int total = 1;
        for (int i = 0; i < k; i++) {
            total *= 3;
        }
        for (int code = 0; code < total; code++) {
            int[] plan = new int[k];
            int c = code;
            for (int i = 0; i < k; i++) {
                plan[i] = c % 3 - 1;
                c /= 3;
            }
            long sum = ScalePans.fromDigits(plan);
            assertThat(seen.put(sum, plan)).as("sum %d twice", sum).isNull();
        }
        assertThat(seen).hasSize(total);
        for (long load = -1093; load <= 1093; load++) {
            int[] want = seen.get(load);
            int[] got = ScalePans.digits(load);
            for (int i = 0; i < k; i++) {
                assertThat(i < got.length ? got[i] : 0).as("load=%d i=%d", load, i).isEqualTo(want[i]);
            }
        }
    }

    @Test
    void roundTripAndPlacement() {
        SplittableRandom rnd = new SplittableRandom(298);
        for (int t = 0; t < 5000; t++) {
            long load = rnd.nextLong(-ScalePans.MAX_LOAD, ScalePans.MAX_LOAD);
            assertThat(ScalePans.fromDigits(ScalePans.digits(load))).isEqualTo(load);
            long far = ScalePans.weights(load, false).stream().mapToLong(Long::longValue).sum();
            long near = ScalePans.weights(load, true).stream().mapToLong(Long::longValue).sum();
            assertThat(far - near).isEqualTo(load);
        }
        assertThat(ScalePans.weights(2, false)).containsExactly(3L);
        assertThat(ScalePans.weights(2, true)).containsExactly(1L);
        assertThat(ScalePans.weightsUsed(40)).isEqualTo(4);
        assertThat(ScalePans.digits(0)).isEmpty();
    }

    @Test
    void questAndBounds() {
        assertThat(ScalePans.quest(5, new int[] {-1, -1, 1})).isTrue();
        assertThat(ScalePans.quest(5, new int[] {2, 1})).isFalse();
        assertThat(ScalePans.quest(5, new int[] {1, 1})).isFalse();
        assertThat(ScalePans.QUEST_ID).isEqualTo("q_scale_pans");
        assertThatThrownBy(() -> ScalePans.digits(Long.MAX_VALUE)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ScalePans.fromDigits(new int[] {3})).isInstanceOf(IllegalArgumentException.class);
    }
}