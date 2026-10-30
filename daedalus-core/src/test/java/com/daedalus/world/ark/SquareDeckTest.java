// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SquareDeckTest {

    @Test
    void leastMatchesBruteForce() {
        for (long d = 2; d <= 60; d++) {
            long s = SquareDeck.isqrt(d);
            if (s * s == d) {
                continue;
            }
            long y = 1;
            while (true) {
                long rhs = 1 + d * y * y;
                long x = SquareDeck.isqrt(rhs);
                if (x * x == rhs) {
                    break;
                }
                y++;
            }
            SquareDeck.Deck deck = SquareDeck.least(d);
            assertThat(deck.y()).as("D=%d", d).isEqualTo(BigInteger.valueOf(y));
            assertThat(SquareDeck.solves(d, deck.x(), deck.y())).isTrue();
        }
        SquareDeck.Deck d61 = SquareDeck.least(61);
        assertThat(d61.x()).isEqualTo(BigInteger.valueOf(1_766_319_049L));
        assertThat(d61.y()).isEqualTo(BigInteger.valueOf(226_153_980L));
    }

    @Test
    void expansionsAndLargeD() {
        assertThat(SquareDeck.expansion(7)).containsExactly(2L, 1L, 1L, 1L, 4L);
        assertThat(SquareDeck.expansion(13)).containsExactly(3L, 1L, 1L, 1L, 1L, 6L);
        assertThat(SquareDeck.period(2)).isEqualTo(1);
        SplittableRandom rnd = new SplittableRandom(283);
        for (int t = 0; t < 150; t++) {
            long d = rnd.nextLong(2, SquareDeck.MAX_D + 1);
            long s = SquareDeck.isqrt(d);
            if (s * s == d) {
                continue;
            }
            SquareDeck.Deck deck = SquareDeck.least(d);
            assertThat(SquareDeck.solves(d, deck.x(), deck.y())).as("D=%d", d).isTrue();
            SquareDeck.Deck third = SquareDeck.nth(d, 3);
            assertThat(SquareDeck.solves(d, third.x(), third.y())).isTrue();
            assertThat(third.x()).isGreaterThan(deck.x());
        }
    }

    @Test
    void questAndBounds() {
        assertThat(SquareDeck.quest(2, BigInteger.valueOf(3), BigInteger.valueOf(2))).isTrue();
        assertThat(SquareDeck.quest(2, BigInteger.valueOf(17), BigInteger.valueOf(12))).isTrue();
        assertThat(SquareDeck.quest(2, BigInteger.valueOf(1), BigInteger.ZERO)).isFalse();
        assertThat(SquareDeck.quest(3, BigInteger.valueOf(3), BigInteger.valueOf(2))).isFalse();
        assertThat(SquareDeck.nth(2, 2)).isEqualTo(new SquareDeck.Deck(BigInteger.valueOf(17), BigInteger.valueOf(12)));
        assertThat(SquareDeck.QUEST_ID).isEqualTo("q_square_deck");
        assertThatThrownBy(() -> SquareDeck.least(49)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SquareDeck.least(1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SquareDeck.nth(2, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThat(List.of(SquareDeck.least(5).x(), SquareDeck.least(5).y())).containsExactly(BigInteger.valueOf(9), BigInteger.valueOf(4));
    }
}