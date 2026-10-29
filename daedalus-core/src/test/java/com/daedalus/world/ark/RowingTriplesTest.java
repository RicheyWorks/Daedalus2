// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class RowingTriplesTest {

    private static boolean bruteExists(int n) {
        if (n * (n - 1) % 6 != 0) {
            return false;
        }
        List<int[]> all = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                for (int c = b + 1; c < n; c++) {
                    all.add(new int[] {a, b, c});
                }
            }
        }
        return choose(n, all, 0, new int[n * (n - 1) / 6][], 0);
    }

    private static boolean choose(int n, List<int[]> all, int start, int[][] pick, int k) {
        if (k == pick.length) {
            return RowingTriples.isSystem(n, pick);
        }
        for (int i = start; i < all.size(); i++) {
            pick[k] = all.get(i);
            if (choose(n, all, i + 1, pick, k + 1)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void existenceMatchesBruteForceSmall() {
        for (int n = 1; n <= 7; n++) {
            assertThat(RowingTriples.exists(n)).isEqualTo(bruteExists(n));
        }
    }

    @Test
    void builderMatchesRuleUpToFifteen() {
        for (int n = 1; n <= 15; n++) {
            int[][] boats = RowingTriples.build(n);
            if (RowingTriples.exists(n)) {
                assertThat(boats.length).isEqualTo(n * (n - 1) / 6);
                assertThat(RowingTriples.isSystem(n, boats)).isTrue();
            } else {
                assertThat(boats.length).isZero();
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(RowingTriples.QUEST_ID).isEqualTo("q_rowing_triples");
        int[][] fano = {{0, 1, 2}, {0, 3, 4}, {0, 5, 6}, {1, 3, 5}, {1, 4, 6}, {2, 3, 6}, {2, 4, 5}};
        assertThat(RowingTriples.quest(7, fano)).isTrue();
        assertThat(RowingTriples.quest(7, new int[][] {{0, 1, 2}})).isFalse();
        assertThatThrownBy(() -> RowingTriples.build(16)).isInstanceOf(IllegalArgumentException.class);
    }
}