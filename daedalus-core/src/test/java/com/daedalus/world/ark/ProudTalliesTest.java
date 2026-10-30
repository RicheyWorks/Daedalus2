// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class ProudTalliesTest {

    @Test
    void searchMatchesBruteScanUpToSevenDigits() {
        List<Long> brute = new ArrayList<>();
        for (long v = 1; v < 10_000_000L; v++) {
            if (ProudTallies.isProud(v)) {
                brute.add(v);
            }
        }
        List<Long> fast = new ArrayList<>();
        for (int len = 1; len <= 7; len++) {
            for (long v : ProudTallies.withDigits(len)) {
                fast.add(v);
            }
        }
        assertThat(fast).isEqualTo(brute);
    }

    @Test
    void knownListToNineDigits() {
        assertThat(ProudTallies.withDigits(3)).containsExactly(153, 370, 371, 407);
        assertThat(ProudTallies.withDigits(2)).isEmpty();
        assertThat(ProudTallies.withDigits(8)).containsExactly(24_678_050L, 24_678_051L, 88_593_477L);
        assertThat(ProudTallies.withDigits(9))
                .containsExactly(146_511_208L, 472_335_975L, 534_494_836L, 912_985_153L);
    }

    @Test
    void questAndGuards() {
        assertThat(ProudTallies.QUEST_ID).isEqualTo("q_proud_tallies");
        assertThat(ProudTallies.quest(4, 1634)).isTrue();
        assertThat(ProudTallies.quest(4, 1635)).isFalse();
        assertThat(ProudTallies.quest(3, 1634)).isFalse();
        assertThatThrownBy(() -> ProudTallies.withDigits(13)).isInstanceOf(IllegalArgumentException.class);
    }
}