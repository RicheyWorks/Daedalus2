// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class CleanLotsTest {

    private static int naiveMu(int n) {
        int m = n;
        int sign = 1;
        for (int p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                m /= p;
                if (m % p == 0) {
                    return 0;
                }
                sign = -sign;
            }
        }
        return m > 1 ? -sign : sign;
    }

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }

    @Test
    void mobiusAndCountsMatchBruteForce() {
        int[] mu = CleanLots.mobius(30_000);
        long clean = 0;
        long mert = 0;
        for (int n = 1; n < 30_000; n++) {
            assertThat(mu[n]).as("n=%d", n).isEqualTo(naiveMu(n));
            clean += mu[n] != 0 ? 1 : 0;
            mert += mu[n];
            if (n % 997 == 0 || n < 200) {
                assertThat(CleanLots.cleanCount(n)).isEqualTo(clean);
                assertThat(CleanLots.mertens(n)).isEqualTo(mert);
            }
        }
        for (int n = 1; n <= 150; n++) {
            long pairs = 0;
            for (int a = 1; a <= n; a++) {
                for (int b = 1; b <= n; b++) {
                    if (gcd(a, b) == 1) {
                        pairs++;
                    }
                }
            }
            assertThat(CleanLots.coprimePairs(n)).isEqualTo(pairs);
        }
    }

    @Test
    void knownValues() {
        assertThat(CleanLots.cleanCount(1_000_000)).isEqualTo(607_926);
        assertThat(CleanLots.cleanCount(1_000_000_000_000L)).isEqualTo(607_927_102_274L);
        assertThat(CleanLots.mertens(1000)).isEqualTo(2);
        assertThat(CleanLots.cleanCount(0)).isZero();
    }

    @Test
    void questAndBounds() {
        assertThat(CleanLots.quest(10, 7)).isTrue();
        assertThat(CleanLots.quest(10, 6)).isFalse();
        assertThat(CleanLots.QUEST_ID).isEqualTo("q_clean_lots");
        assertThatThrownBy(() -> CleanLots.mobius(1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CleanLots.cleanCount(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}