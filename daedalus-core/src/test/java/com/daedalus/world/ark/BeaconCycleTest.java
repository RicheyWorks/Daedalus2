// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.OptionalLong;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BeaconCycleTest {

    @Test
    void matchesBruteForceForSmallPrimes() {
        for (long p = 2; p < 400; p++) {
            if (!LanternHandshake.isPrime(p)) {
                continue;
            }
            long root = -1;
            for (long g = 1; g < p; g++) {
                long[] first = new long[(int) p];
                java.util.Arrays.fill(first, -1);
                long v = 1;
                long ord = 0;
                do {
                    first[(int) v] = ord;
                    v = v * g % p;
                    ord++;
                } while (v != 1);
                assertThat(BeaconCycle.order(g, p)).as("g=%d p=%d", g, p).isEqualTo(ord);
                if (root < 0 && ord == p - 1) {
                    root = g;
                }
                for (long h = 0; h < p; h++) {
                    OptionalLong x = BeaconCycle.steps(g, h, p);
                    if (first[(int) h] < 0) {
                        assertThat(x).isEmpty();
                    } else {
                        assertThat(x).hasValue(first[(int) h]);
                    }
                }
            }
            assertThat(BeaconCycle.primitiveRoot(p)).isEqualTo(root);
        }
    }

    @Test
    void largePrimes() {
        assertThat(BeaconCycle.primitiveRoot(1_000_000_007L)).isEqualTo(5);
        SplittableRandom rnd = new SplittableRandom(314);
        long p = 2_147_483_647L;
        for (int t = 0; t < 30; t++) {
            long x = rnd.nextLong(0, p - 1);
            long h = LanternHandshake.powMod(7, x, p);
            assertThat(BeaconCycle.steps(7, h, p)).hasValue(x);
        }
    }

    @Test
    void questAndBounds() {
        assertThat(BeaconCycle.quest(3, 13, 17, 4)).isTrue();
        assertThat(BeaconCycle.quest(3, 13, 17, 5)).isFalse();
        assertThat(BeaconCycle.QUEST_ID).isEqualTo("q_beacon_cycle");
        assertThatThrownBy(() -> BeaconCycle.order(2, 15)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeaconCycle.order(17, 17)).isInstanceOf(IllegalArgumentException.class);
    }
}