// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class BuntingFlagsTest {

    private static int[] orbitCounts(int n, int k) {
        Set<String> neck = new HashSet<>();
        Set<String> brace = new HashSet<>();
        int total = 1;
        for (int i = 0; i < n; i++) {
            total *= k;
        }
        int[] ring = new int[n];
        for (int code = 0; code < total; code++) {
            int c = code;
            for (int i = 0; i < n; i++) {
                ring[i] = c % k;
                c /= k;
            }
            neck.add(Arrays.toString(BuntingFlags.canonical(ring, false)));
            brace.add(Arrays.toString(BuntingFlags.canonical(ring, true)));
        }
        return new int[] {neck.size(), brace.size()};
    }

    @Test
    void burnsideMatchesBruteOrbits() {
        for (int k = 1; k <= 4; k++) {
            for (int n = 1; n <= 9 && Math.pow(k, n) <= 300_000; n++) {
                int[] want = orbitCounts(n, k);
                assertThat(BuntingFlags.necklaces(n, k)).as("n=%d k=%d", n, k).isEqualTo(BigInteger.valueOf(want[0]));
                assertThat(BuntingFlags.bracelets(n, k)).as("n=%d k=%d", n, k).isEqualTo(BigInteger.valueOf(want[1]));
            }
        }
        assertThat(BuntingFlags.necklaces(6, 2)).isEqualTo(BigInteger.valueOf(14));
        assertThat(BuntingFlags.bracelets(6, 2)).isEqualTo(BigInteger.valueOf(13));
        assertThat(BuntingFlags.necklaces(30, 2)).isEqualTo(BigInteger.valueOf(35_792_568L));
    }

    @Test
    void phiAndCanonical() {
        int[] want = {1, 1, 2, 2, 4, 2, 6, 4, 6, 4, 10, 4};
        for (int n = 1; n <= want.length; n++) {
            assertThat(BuntingFlags.phi(n)).isEqualTo(want[n - 1]);
        }
        assertThat(BuntingFlags.canonical(new int[] {2, 0, 1}, false)).containsExactly(0, 1, 2);
        assertThat(BuntingFlags.canonical(new int[] {2, 1, 0}, true)).containsExactly(0, 1, 2);
        assertThat(BuntingFlags.canonical(new int[] {2, 1, 0}, false)).containsExactly(0, 2, 1);
    }

    @Test
    void questAndBounds() {
        assertThat(BuntingFlags.quest(new int[] {0, 0, 1, 2}, new int[] {2, 1, 0, 0}, true)).isTrue();
        assertThat(BuntingFlags.quest(new int[] {0, 1, 0, 1}, new int[] {0, 0, 1, 1}, false)).isTrue();
        assertThat(BuntingFlags.quest(new int[] {0, 1, 0, 1}, new int[] {0, 0, 1, 1}, true)).isFalse();
        assertThat(BuntingFlags.QUEST_ID).isEqualTo("q_bunting_flags");
        assertThatThrownBy(() -> BuntingFlags.necklaces(0, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BuntingFlags.bracelets(3, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BuntingFlags.canonical(new int[0], true)).isInstanceOf(IllegalArgumentException.class);
    }
}