// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class BeaconWeightsTest {

    private static int[] subset(int mask, int n) {
        int[] out = new int[Integer.bitCount(mask)];
        int k = 0;
        for (int v = 1; v <= n; v++) {
            if ((mask >> (v - 1) & 1) != 0) {
                out[k++] = v;
            }
        }
        return out;
    }

    @Test
    void largestMatchesBruteForceSubsets() {
        for (int n = 1; n <= 16; n++) {
            int want = 0;
            for (int mask = 1; mask < (1 << n); mask++) {
                int bits = Integer.bitCount(mask);
                if (bits > want && BeaconWeights.isSidon(subset(mask, n))) {
                    want = bits;
                }
            }
            int[] got = BeaconWeights.largest(n);
            assertThat(got).hasSize(want);
            assertThat(BeaconWeights.isSidon(got)).isTrue();
            assertThat(got[got.length - 1]).isLessThanOrEqualTo(n);
        }
    }

    @Test
    void mianChowlaKnownTerms() {
        assertThat(BeaconWeights.mianChowla(20)).containsExactly(1, 2, 4, 8, 13, 21, 31, 45, 66, 81, 97, 123,
                148, 182, 204, 252, 290, 361, 401, 475);
        assertThat(BeaconWeights.isSidon(BeaconWeights.mianChowla(200))).isTrue();
    }

    @Test
    void questAndGuards() {
        assertThat(BeaconWeights.QUEST_ID).isEqualTo("q_beacon_weights");
        assertThat(BeaconWeights.quest(4, 7, new int[] {1, 2, 5, 7})).isTrue();
        assertThat(BeaconWeights.quest(4, 7, new int[] {1, 2, 3, 7})).isFalse();
        assertThat(BeaconWeights.isSidon(new int[] {3, 3})).isFalse();
        assertThatThrownBy(() -> BeaconWeights.largest(41)).isInstanceOf(IllegalArgumentException.class);
    }
}