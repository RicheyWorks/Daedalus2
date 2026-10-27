// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class HailstoneDriftTest {

    @Test
    void tableMatchesNaive() {
        int[] t = HailstoneDrift.table(20_000);
        for (int n = 1; n < 20_000; n++) {
            assertThat(t[n]).as("n=%d", n).isEqualTo(HailstoneDrift.steps(n));
        }
        assertThat(HailstoneDrift.steps(27)).isEqualTo(111);
        assertThat(HailstoneDrift.peak(27)).isEqualTo(9232);
        assertThat(HailstoneDrift.steps(1)).isZero();
    }

    @Test
    void longestAndRecords() {
        assertThat(HailstoneDrift.longest(1_000_000)).isEqualTo(837_799);
        assertThat(HailstoneDrift.steps(837_799)).isEqualTo(524);
        assertThat(HailstoneDrift.records(1000)).containsExactly(
                1, 2, 3, 6, 7, 9, 18, 25, 27, 54, 73, 97, 129, 171, 231, 313, 327, 649, 703, 871);
    }

    @Test
    void questAndBounds() {
        assertThat(HailstoneDrift.quest(6, 8)).isTrue();
        assertThat(HailstoneDrift.quest(6, 7)).isFalse();
        assertThat(HailstoneDrift.QUEST_ID).isEqualTo("q_hailstone_drift");
        assertThatThrownBy(() -> HailstoneDrift.steps(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HailstoneDrift.table(1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HailstoneDrift.steps(Long.MAX_VALUE)).isInstanceOf(ArithmeticException.class);
    }
}