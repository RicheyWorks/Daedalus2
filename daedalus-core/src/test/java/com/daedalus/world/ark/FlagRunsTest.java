// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class FlagRunsTest {

    @Test
    void finderMatchesBruteForceColourings() {
        for (int k = 2; k <= 4; k++) {
            for (int n = 1; n <= 18; n++) {
                boolean want = false;
                int[] line = new int[n];
                for (int mask = 0; !want && mask < (1 << n); mask++) {
                    for (int i = 0; i < n; i++) {
                        line[i] = mask >> i & 1;
                    }
                    want = FlagRuns.isSafe(line, k);
                }
                int[] got = FlagRuns.find(n, k);
                assertThat(got.length == n).isEqualTo(want);
                if (want) {
                    assertThat(FlagRuns.isSafe(got, k)).isTrue();
                }
            }
        }
    }

    @Test
    void knownWaerdenNumbers() {
        assertThat(FlagRuns.waerden(2)).isEqualTo(3);
        assertThat(FlagRuns.waerden(3)).isEqualTo(9);
        assertThat(FlagRuns.waerden(4)).isEqualTo(35);
    }

    @Test
    void questAndGuards() {
        assertThat(FlagRuns.QUEST_ID).isEqualTo("q_flag_runs");
        assertThat(FlagRuns.quest(8, 3, new int[] {0, 0, 1, 1, 0, 0, 1, 1})).isTrue();
        assertThat(FlagRuns.quest(3, 3, new int[] {1, 1, 1})).isFalse();
        assertThatThrownBy(() -> FlagRuns.find(10, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}