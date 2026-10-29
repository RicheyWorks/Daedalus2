// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class PairedPennantsTest {

    private static long brute(int[] line, int pos, int[] left) {
        if (pos == line.length) {
            return PairedPennants.isValid(line) ? 1 : 0;
        }
        long total = 0;
        for (int v = 1; v < left.length; v++) {
            if (left[v] > 0) {
                left[v]--;
                line[pos] = v;
                total += brute(line, pos + 1, left);
                left[v]++;
            }
        }
        return total;
    }

    @Test
    void countMatchesBruteForceMultisetPermutations() {
        for (int n = 1; n <= 6; n++) {
            int[] left = new int[n + 1];
            for (int v = 1; v <= n; v++) {
                left[v] = 2;
            }
            long want = brute(new int[2 * n], 0, left);
            assertThat(PairedPennants.count(n)).isEqualTo(want);
            assertThat(want > 0).isEqualTo(PairedPennants.exists(n));
        }
        assertThat(PairedPennants.count(7)).isEqualTo(52);
        assertThat(PairedPennants.count(8)).isEqualTo(300);
    }

    @Test
    void buildIsValidExactlyWhenExists() {
        for (int n = 1; n <= 16; n++) {
            int[] line = PairedPennants.build(n);
            if (PairedPennants.exists(n)) {
                assertThat(PairedPennants.isValid(line)).isTrue();
            } else {
                assertThat(line).isEmpty();
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(PairedPennants.QUEST_ID).isEqualTo("q_paired_pennants");
        assertThat(PairedPennants.quest(new int[] {3, 1, 2, 1, 3, 2})).isTrue();
        assertThat(PairedPennants.quest(new int[] {1, 1, 2, 2, 3, 3})).isFalse();
        assertThat(PairedPennants.isValid(new int[0])).isFalse();
        assertThatThrownBy(() -> PairedPennants.count(17)).isInstanceOf(IllegalArgumentException.class);
    }
}