// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class TumblerDigitsTest {

    private static long naiveStep(long x, int width) {
        char[] c = String.format("%0" + width + "d", x).toCharArray();
        Arrays.sort(c);
        String asc = new String(c);
        String desc = new StringBuilder(asc).reverse().toString();
        return Long.parseLong(desc) - Long.parseLong(asc);
    }

    @Test
    void decimalStepsMatchStrings() {
        for (int width = 1; width <= 5; width++) {
            long lim = (long) Math.pow(10, width);
            for (long x = 0; x < lim; x++) {
                assertThat(TumblerDigits.step(x, width, 10)).isEqualTo(naiveStep(x, width));
            }
        }
        for (long x = 0; x < 10_000; x++) {
            boolean repdigit = x % 1111 == 0;
            long[] loop = TumblerDigits.loop(x, 4, 10);
            if (repdigit) {
                assertThat(loop).containsExactly(0L);
            } else {
                assertThat(loop).containsExactly(6174L);
                assertThat(TumblerDigits.stepsToLoop(x, 4, 10)).isBetween(0, 7);
            }
        }
        assertThat(TumblerDigits.loop(123, 3, 10)).containsExactly(495L);
        assertThat(TumblerDigits.loop(12, 2, 10)).containsExactly(9L, 81L, 63L, 27L, 45L);
    }

    @Test
    void otherBasesStayInRangeAndLoop() {
        for (int base = 2; base <= 12; base++) {
            for (int width = 1; width <= 4; width++) {
                long lim = 1;
                for (int i = 0; i < width; i++) {
                    lim *= base;
                }
                for (long x = 0; x < lim; x++) {
                    long[] loop = TumblerDigits.loop(x, width, base);
                    assertThat(loop).isNotEmpty();
                    long v = loop[loop.length - 1];
                    assertThat(TumblerDigits.step(v, width, base)).isEqualTo(loop[0]);
                }
            }
        }
    }

    @Test
    void happyQuestAndBounds() {
        List<Long> happy = new ArrayList<>();
        for (long n = 1; n <= 50; n++) {
            if (TumblerDigits.isHappy(n)) {
                happy.add(n);
            }
        }
        assertThat(happy).containsExactly(1L, 7L, 10L, 13L, 19L, 23L, 28L, 31L, 32L, 44L, 49L);
        assertThat(TumblerDigits.quest(6174, 0)).isTrue();
        assertThat(TumblerDigits.quest(3524, 3)).isTrue();
        assertThat(TumblerDigits.quest(3524, 2)).isFalse();
        assertThat(TumblerDigits.QUEST_ID).isEqualTo("q_tumbler_digits");
        assertThatThrownBy(() -> TumblerDigits.step(10_000, 4, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TumblerDigits.step(1, 4, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TumblerDigits.isHappy(0)).isInstanceOf(IllegalArgumentException.class);
    }
}