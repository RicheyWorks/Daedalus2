// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class LogDecimalsTest {

    /** {pre, period} by watching long-division remainders repeat. */
    private static int[] brute(long a, long b, int base) {
        Map<Long, Integer> seen = new HashMap<>();
        long r = a % b;
        int i = 0;
        while (r != 0 && !seen.containsKey(r)) {
            seen.put(r, i++);
            r = r * base % b;
        }
        if (r == 0) {
            return new int[] {i, 0};
        }
        return new int[] {seen.get(r), i - seen.get(r)};
    }

    @Test
    void lengthsMatchRemainderTracking() {
        for (int base = 2; base <= 16; base++) {
            for (long b = 1; b <= 300; b++) {
                for (long a = 0; a <= 2 * b; a += 1 + b / 40) {
                    int[] want = brute(a, b, base);
                    assertThat(LogDecimals.prePeriod(a, b, base)).as("%d/%d base %d", a, b, base).isEqualTo(want[0]);
                    assertThat(LogDecimals.period(a, b, base)).as("%d/%d base %d", a, b, base).isEqualTo(want[1]);
                }
            }
        }
    }

    @Test
    void expansions() {
        assertThat(LogDecimals.expand(1, 7, 10)).isEqualTo("0.(142857)");
        assertThat(LogDecimals.expand(1, 12, 10)).isEqualTo("0.08(3)");
        assertThat(LogDecimals.expand(1, 8, 10)).isEqualTo("0.125");
        assertThat(LogDecimals.expand(22, 7, 10)).isEqualTo("3.(142857)");
        assertThat(LogDecimals.expand(6, 3, 10)).isEqualTo("2");
        assertThat(LogDecimals.expand(1, 3, 2)).isEqualTo("0.(01)");
        assertThat(LogDecimals.expand(1, 10, 16)).isEqualTo("0.1(9)");
        assertThat(LogDecimals.period(1, 97, 10)).isEqualTo(96);
        assertThat(LogDecimals.period(1, 9_999_991, 10)).isPositive();
    }

    @Test
    void questAndBounds() {
        assertThat(LogDecimals.quest(1, 7, 10, 6)).isTrue();
        assertThat(LogDecimals.quest(1, 7, 10, 7)).isFalse();
        assertThat(LogDecimals.quest(3, 4, 10, 0)).isTrue();
        assertThat(LogDecimals.QUEST_ID).isEqualTo("q_log_decimals");
        assertThatThrownBy(() -> LogDecimals.period(1, 0, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LogDecimals.period(1, 3, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LogDecimals.period(-1, 3, 10)).isInstanceOf(IllegalArgumentException.class);
    }
}