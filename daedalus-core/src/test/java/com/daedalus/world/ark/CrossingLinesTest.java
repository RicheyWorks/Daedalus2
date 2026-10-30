// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CrossingLinesTest {

    private static boolean brute(long[][] s) {
        for (int i = 0; i < s.length; i++) {
            for (int j = i + 1; j < s.length; j++) {
                if (CrossingLines.meet(s[i], s[j])) {
                    return true;
                }
            }
        }
        return false;
    }

    private static void check(long[][] s) {
        int[] p = CrossingLines.findPair(s);
        assertThat(p.length == 2).isEqualTo(brute(s));
        if (p.length == 2) {
            assertThat(p[0]).isLessThan(p[1]);
            assertThat(CrossingLines.meet(s[p[0]], s[p[1]])).isTrue();
        }
    }

    @Test
    void handBuiltCases() {
        long[][] x = {{0, 0, 4, 4}, {0, 4, 4, 0}};
        assertThat(CrossingLines.findPair(x)).containsExactly(0, 1);
        long[][] apart = {{0, 0, 4, 0}, {0, 1, 4, 1}, {5, 0, 5, 3}};
        assertThat(CrossingLines.findPair(apart)).isEmpty();
        long[][] touch = {{0, 0, 2, 2}, {2, 2, 4, 0}};
        assertThat(CrossingLines.findPair(touch)).containsExactly(0, 1);
        long[][] vert = {{0, 5, 10, 5}, {5, 0, 5, 10}};
        assertThat(CrossingLines.quest(vert, true)).isTrue();
        assertThat(CrossingLines.quest(apart, false)).isTrue();
    }

    @Test
    void randomTinyGridsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(455);
        for (int it = 0; it < 20_000; it++) {
            int n = 1 + r.nextInt(6);
            int span = 2 + r.nextInt(6);
            long[][] s = new long[n][];
            for (int i = 0; i < n; i++) {
                s[i] = new long[] {r.nextInt(span), r.nextInt(span), r.nextInt(span), r.nextInt(span)};
            }
            check(s);
        }
    }

    @Test
    void randomShortLinesMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(4550);
        for (int it = 0; it < 300; it++) {
            int n = 2 + r.nextInt(200);
            long[][] s = new long[n][];
            for (int i = 0; i < n; i++) {
                long x = r.nextInt(-100_000, 99_000);
                long y = r.nextInt(-99_000, 99_000);
                s[i] = new long[] {x, y, x + r.nextInt(1000), y + r.nextInt(-500, 1000)};
            }
            check(s);
        }
    }

    @Test
    void largestParallelFleetHasNoMeeting() {
        long[][] s = new long[CrossingLines.MAX_LINES][];
        for (int i = 0; i < s.length; i++) {
            s[i] = new long[] {-100_000, 2L * i, 100_000, 2L * i + 1};
        }
        assertThat(CrossingLines.findPair(s)).isEmpty();
        s[4999] = new long[] {0, -100_000, 0, 100_000};
        assertThat(CrossingLines.findPair(s)).hasSize(2);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> CrossingLines.findPair(new long[0][]))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrossingLines.findPair(new long[][] {{0, 0, 1}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrossingLines.findPair(new long[][] {{0, 0, 200_000, 0}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}