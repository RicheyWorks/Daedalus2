// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.List;
import org.junit.jupiter.api.Test;

class BallastSplitsTest {

    @Test
    void knownPartitionNumbers() {
        long[] small = {1, 1, 2, 3, 5, 7, 11, 15, 22, 30, 42};
        for (int n = 0; n < small.length; n++) {
            assertThat(BallastSplits.count(n)).isEqualTo(BigInteger.valueOf(small[n]));
        }
        assertThat(BallastSplits.count(100)).isEqualTo(new BigInteger("190569292"));
        assertThat(BallastSplits.count(1000)).isEqualTo(
            new BigInteger("24061467864032622473692149727991"));
    }

    @Test
    void recurrenceDpAndListingAgree() {
        for (int n = 0; n <= 25; n++) {
            assertThat(BallastSplits.countAtMost(n, n)).isEqualTo(BallastSplits.count(n));
            assertThat(BallastSplits.list(n)).hasSize(BallastSplits.count(n).intValueExact());
        }
        for (int n = 0; n <= 300; n += 7) {
            assertThat(BallastSplits.countAtMost(n, n)).isEqualTo(BallastSplits.count(n));
        }
        for (int n = 1; n <= 20; n++) {
            for (int k = 0; k <= n; k++) {
                final int cap = k;
                long brute = BallastSplits.list(n).stream().filter(s -> s.size() <= cap).count();
                assertThat(BallastSplits.countAtMost(n, k)).isEqualTo(BigInteger.valueOf(brute));
            }
        }
    }

    @Test
    void listingQuestAndBounds() {
        assertThat(BallastSplits.list(4)).containsExactly(
            List.of(4), List.of(3, 1), List.of(2, 2), List.of(2, 1, 1), List.of(1, 1, 1, 1));
        assertThat(BallastSplits.list(0)).containsExactly(List.of());
        assertThat(BallastSplits.countAtMost(10, 2)).isEqualTo(BigInteger.valueOf(6));
        assertThat(BallastSplits.quest(5, "7")).isTrue();
        assertThat(BallastSplits.quest(5, "8")).isFalse();
        assertThat(BallastSplits.QUEST_ID).isEqualTo("q_ballast_splits");
        assertThatThrownBy(() -> BallastSplits.count(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BallastSplits.list(41)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BallastSplits.countAtMost(3, -1)).isInstanceOf(IllegalArgumentException.class);
    }
}
