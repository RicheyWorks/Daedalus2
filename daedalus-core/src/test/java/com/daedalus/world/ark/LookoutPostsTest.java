// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class LookoutPostsTest {

    private static final long[] KNOWN = {1, 0, 0, 2, 10, 4, 40, 92, 352, 724, 2680, 14200};

    @Test
    void countsMatchKnownValues() {
        for (int n = 1; n <= KNOWN.length; n++) {
            assertThat(LookoutPosts.count(n)).as("n=%d", n).isEqualTo(KNOWN[n - 1]);
        }
    }

    @Test
    void countsMatchPermutationBruteForce() {
        for (int n = 1; n <= 8; n++) {
            assertThat(LookoutPosts.count(n)).isEqualTo(brute(n, 0, new int[n], new boolean[n]));
        }
    }

    @Test
    void firstLayoutIsValidOrAbsent() {
        for (int n = 1; n <= 16; n++) {
            var f = LookoutPosts.first(n);
            if (n == 2 || n == 3) {
                assertThat(f).isEmpty();
            } else {
                assertThat(f).isPresent();
                assertThat(LookoutPosts.valid(f.get())).as("n=%d", n).isTrue();
            }
        }
        assertThat(LookoutPosts.first(4).orElseThrow()).containsExactly(1, 3, 0, 2);
    }

    @Test
    void questAndValidation() {
        assertThat(LookoutPosts.quest(4, new int[] {2, 0, 3, 1})).isTrue();
        assertThat(LookoutPosts.quest(4, new int[] {0, 1, 2, 3})).isFalse();
        assertThat(LookoutPosts.quest(4, new int[] {1, 3, 0})).isFalse();
        assertThat(LookoutPosts.quest(4, new int[] {1, 3, 0, 4})).isFalse();
        assertThat(LookoutPosts.QUEST_ID).isEqualTo("q_lookout_posts");
        assertThatThrownBy(() -> LookoutPosts.count(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LookoutPosts.first(17)).isInstanceOf(IllegalArgumentException.class);
    }

    private static long brute(int n, int row, int[] cols, boolean[] used) {
        if (row == n) {
            return LookoutPosts.valid(cols) ? 1 : 0;
        }
        long total = 0;
        for (int c = 0; c < n; c++) {
            if (!used[c]) {
                used[c] = true;
                cols[row] = c;
                total += brute(n, row + 1, cols, used);
                used[c] = false;
            }
        }
        return total;
    }
}
