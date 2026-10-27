// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

class MooringArcsTest {

    /** Every partner assignment (free or any pairing), counted when it is a valid layout. */
    private static void brute(int[] p, int i, boolean full, long[] out) {
        int n = p.length;
        while (i < n && p[i] != -2) {
            i++;
        }
        if (i == n) {
            if (MooringArcs.isLayout(p)) {
                int adjacent = 0;
                for (int a = 0; a + 1 < n; a++) {
                    if (p[a] == a + 1) {
                        adjacent++;
                    }
                }
                out[full ? adjacent : 0]++;
            }
            return;
        }
        if (!full) {
            p[i] = -1;
            brute(p, i + 1, full, out);
        }
        for (int j = i + 1; j < n; j++) {
            if (p[j] == -2) {
                p[i] = j;
                p[j] = i;
                brute(p, i + 1, full, out);
                p[j] = -2;
            }
        }
        p[i] = -2;
    }

    @Test
    void motzkinMatchesBruteForce() {
        for (int n = 0; n <= 11; n++) {
            int[] p = new int[n];
            Arrays.fill(p, -2);
            long[] out = new long[1];
            brute(p, 0, false, out);
            assertThat(MooringArcs.motzkin(n)).isEqualTo(BigInteger.valueOf(out[0]));
        }
        assertThat(MooringArcs.motzkin(20)).isEqualTo(BigInteger.valueOf(50_852_019L));
    }

    @Test
    void narayanaMatchesBruteForce() {
        for (int n = 1; n <= 6; n++) {
            int[] p = new int[2 * n];
            Arrays.fill(p, -2);
            long[] out = new long[n + 1];
            brute(p, 0, true, out);
            for (int k = 1; k <= n; k++) {
                assertThat(MooringArcs.narayana(n, k)).isEqualTo(BigInteger.valueOf(out[k]));
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(MooringArcs.QUEST_ID).isEqualTo("q_mooring_arcs");
        assertThat(MooringArcs.quest(4, BigInteger.valueOf(9))).isTrue();
        assertThat(MooringArcs.quest(4, BigInteger.valueOf(8))).isFalse();
        assertThat(MooringArcs.isLayout(new int[] {2, 3, 0, 1})).isFalse();
        assertThat(MooringArcs.isLayout(new int[] {3, 2, 1, 0})).isTrue();
        assertThatThrownBy(() -> MooringArcs.motzkin(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}