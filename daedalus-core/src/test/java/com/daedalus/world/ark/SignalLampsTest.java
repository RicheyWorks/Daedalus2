// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SignalLampsTest {

    @Test
    void tourIsAValidSingleFlipCycleForEveryMastUpTo12() {
        for (int n = 1; n <= 12; n++) {
            int[] t = SignalLamps.tour(n);
            assertThat(SignalLamps.validTour(n, t)).as("n=%d", n).isTrue();
            for (int i = 0; i < t.length; i++) {
                int next = t[(i + 1) % t.length];
                assertThat(t[i] ^ next).isEqualTo(1 << SignalLamps.flipAt(n, i));
            }
        }
    }

    @Test
    void rankInvertsPattern() {
        for (int i = 0; i < (1 << 16); i++) {
            assertThat(SignalLamps.rank(SignalLamps.pattern(i))).isEqualTo(i);
        }
        assertThat(SignalLamps.rank(SignalLamps.pattern(Integer.MAX_VALUE))).isEqualTo(Integer.MAX_VALUE);
    }

    @Test
    void knownThreeLampTour() {
        assertThat(SignalLamps.tour(3)).containsExactly(0, 1, 3, 2, 6, 7, 5, 4);
        assertThat(SignalLamps.flipAt(3, 7)).isEqualTo(2);
        assertThat(SignalLamps.flipAt(30, 0)).isZero();
    }

    @Test
    void badLogsFailTheQuest() {
        assertThat(SignalLamps.quest(2, new int[] {0, 1, 3, 2})).isTrue();
        assertThat(SignalLamps.quest(2, new int[] {0, 1, 2, 3})).isFalse();
        assertThat(SignalLamps.quest(2, new int[] {0, 1, 3, 1})).isFalse();
        assertThat(SignalLamps.quest(2, new int[] {1, 0, 2, 3})).isFalse();
        assertThat(SignalLamps.quest(2, new int[] {0, 1, 3})).isFalse();
        assertThat(SignalLamps.QUEST_ID).isEqualTo("q_signal_lamps");
    }

    @Test
    void validation() {
        assertThatThrownBy(() -> SignalLamps.tour(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalLamps.tour(21)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalLamps.flipAt(3, 8)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalLamps.pattern(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalLamps.rank(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}
