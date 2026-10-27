// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SonarPingsTest {

    private static long brute(int[] a, int k) {
        if (k == a.length) {
            return SonarPings.isCostas(a) ? 1 : 0;
        }
        long t = 0;
        for (int i = k; i < a.length; i++) {
            int x = a[k];
            a[k] = a[i];
            a[i] = x;
            t += brute(a, k + 1);
            a[i] = a[k];
            a[k] = x;
        }
        return t;
    }

    @Test
    void countMatchesBruteForcePermutations() {
        for (int n = 1; n <= 8; n++) {
            int[] id = new int[n];
            for (int i = 0; i < n; i++) {
                id[i] = i;
            }
            assertThat(SonarPings.count(n)).isEqualTo(brute(id, 0));
        }
    }

    @Test
    void knownCountsAndWelch() {
        long[] known = {1, 2, 4, 12, 40, 116, 200, 444, 760, 2160};
        for (int n = 1; n <= 10; n++) {
            assertThat(SonarPings.count(n)).isEqualTo(known[n - 1]);
        }
        int[] primes = {2, 3, 5, 7, 11, 13, 31, 101, 257};
        for (int p : primes) {
            assertThat(SonarPings.isCostas(SonarPings.welch(p))).isTrue();
        }
    }

    @Test
    void questAndGuards() {
        assertThat(SonarPings.QUEST_ID).isEqualTo("q_sonar_pings");
        assertThat(SonarPings.quest(3, new int[] {0, 2, 1})).isTrue();
        assertThat(SonarPings.quest(3, new int[] {0, 1, 2})).isFalse();
        assertThatThrownBy(() -> SonarPings.welch(12)).isInstanceOf(IllegalArgumentException.class);
    }
}