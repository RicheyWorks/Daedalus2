// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class HammockSwapTest {

    private static int[] bruteHome(int n) {
        int[] byHome = new int[n + 1];
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = i;
        }
        permute(p, 0, byHome);
        return byHome;
    }

    private static void permute(int[] p, int k, int[] byHome) {
        if (k == p.length) {
            int home = 0;
            for (int i = 0; i < p.length; i++) {
                if (p[i] == i) {
                    home++;
                }
            }
            byHome[home]++;
            return;
        }
        for (int i = k; i < p.length; i++) {
            swap(p, k, i);
            permute(p, k + 1, byHome);
            swap(p, k, i);
        }
    }

    private static void swap(int[] p, int i, int j) {
        int t = p[i];
        p[i] = p[j];
        p[j] = t;
    }

    @Test
    void matchesBruteForce() {
        for (int n = 0; n <= 8; n++) {
            int[] byHome = bruteHome(n);
            assertThat(HammockSwap.count(n)).as("n=%d", n).isEqualTo(BigInteger.valueOf(byHome[0]));
            for (int k = 0; k <= n; k++) {
                assertThat(HammockSwap.exactlyHome(n, k)).isEqualTo(BigInteger.valueOf(byHome[k]));
            }
        }
        assertThat(HammockSwap.count(20)).isEqualTo(new BigInteger("895014631192902121"));
    }

    @Test
    void modMatchesExact() {
        SplittableRandom rnd = new SplittableRandom(277);
        for (int t = 0; t < 300; t++) {
            int n = rnd.nextInt(0, 400);
            long m = rnd.nextLong(1, Integer.MAX_VALUE + 1L);
            assertThat(HammockSwap.countMod(n, m)).isEqualTo(HammockSwap.count(n).mod(BigInteger.valueOf(m)).longValue());
        }
    }

    @Test
    void drawIsUniformSwap() {
        SplittableRandom rnd = new SplittableRandom(42);
        Map<String, Integer> hits = new HashMap<>();
        for (int t = 0; t < 45_000; t++) {
            int[] p = HammockSwap.draw(4, rnd);
            assertThat(HammockSwap.isSwap(p)).isTrue();
            hits.merge(Arrays.toString(p), 1, Integer::sum);
        }
        assertThat(hits).hasSize(9);
        assertThat(hits.values()).allSatisfy(v -> assertThat(v).isBetween(4_600, 5_400));
    }

    @Test
    void questAndBounds() {
        assertThat(HammockSwap.quest(3, new int[] {1, 2, 0})).isTrue();
        assertThat(HammockSwap.quest(3, new int[] {1, 0, 2})).isFalse();
        assertThat(HammockSwap.quest(3, new int[] {1, 1, 0})).isFalse();
        assertThat(HammockSwap.quest(4, new int[] {1, 2, 0})).isFalse();
        assertThat(HammockSwap.QUEST_ID).isEqualTo("q_hammock_swap");
        assertThatThrownBy(() -> HammockSwap.count(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HammockSwap.draw(1, new SplittableRandom(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HammockSwap.countMod(5, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}