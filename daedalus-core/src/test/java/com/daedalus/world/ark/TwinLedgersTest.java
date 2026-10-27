// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class TwinLedgersTest {

    @Test
    void sieveMatchesTrialDivision() {
        long[] s = TwinLedgers.sieve(30_000);
        for (int n = 1; n < 30_000; n++) {
            long naive = 0;
            for (int d = 1; d < n; d++) {
                if (n % d == 0) {
                    naive += d;
                }
            }
            if (n < 3000) {
                assertThat(s[n]).as("n=%d", n).isEqualTo(naive);
            }
            assertThat(TwinLedgers.properSum(n)).isEqualTo(s[n]);
        }
    }

    @Test
    void perfectTwinsAndChains() {
        List<Long> perfect = new ArrayList<>();
        for (long n = 1; n < 10_000; n++) {
            if (TwinLedgers.grade(n) == TwinLedgers.Grade.PERFECT) {
                perfect.add(n);
            }
        }
        assertThat(perfect).containsExactly(6L, 28L, 496L, 8128L);
        assertThat(TwinLedgers.grade(12)).isEqualTo(TwinLedgers.Grade.ABUNDANT);
        assertThat(TwinLedgers.grade(13)).isEqualTo(TwinLedgers.Grade.DEFICIENT);
        assertThat(TwinLedgers.grade(33_550_336L)).isEqualTo(TwinLedgers.Grade.PERFECT);
        List<long[]> twins = TwinLedgers.twins(10_000);
        assertThat(twins).extracting(p -> p[0] + "-" + p[1])
                .containsExactly("220-284", "1184-1210", "2620-2924", "5020-5564", "6232-6368");
        TwinLedgers.Chain sociable = TwinLedgers.chain(12_496, 50);
        assertThat(sociable.terms()).containsExactly(12_496L, 14_288L, 15_472L, 14_536L, 14_264L);
        assertThat(sociable.loopStart()).isZero();
        TwinLedgers.Chain ends = TwinLedgers.chain(10, 50);
        assertThat(ends.terms()).containsExactly(10L, 8L, 7L, 1L, 0L);
        assertThat(ends.loopStart()).isEqualTo(-1);
        assertThat(TwinLedgers.chain(95, 50).loopStart()).isEqualTo(2);
    }

    @Test
    void questAndBounds() {
        assertThat(TwinLedgers.quest(220, 284)).isTrue();
        assertThat(TwinLedgers.quest(284, 220)).isTrue();
        assertThat(TwinLedgers.quest(6, 0)).isTrue();
        assertThat(TwinLedgers.quest(10, 0)).isTrue();
        assertThat(TwinLedgers.quest(220, 0)).isFalse();
        assertThat(TwinLedgers.QUEST_ID).isEqualTo("q_twin_ledgers");
        assertThatThrownBy(() -> TwinLedgers.sieve(1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TwinLedgers.properSum(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TwinLedgers.chain(5, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}