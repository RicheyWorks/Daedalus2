// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class MessTableTest {

    private static boolean bruteExists(int n, int s, int t) {
        int edges = n * (n - 1) / 2;
        for (int mask = 0; mask < (1 << edges); mask++) {
            boolean[][] g = new boolean[n][n];
            int e = 0;
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j < n; j++) {
                    boolean b = (mask >> e++ & 1) != 0;
                    g[i][j] = b;
                    g[j][i] = b;
                }
            }
            if (MessTable.isPeaceful(g, s, t)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void finderMatchesBruteForceColourings() {
        int[][] pairs = {{3, 3}, {3, 4}, {2, 4}, {4, 4}};
        for (int[] p : pairs) {
            for (int n = 1; n <= 6; n++) {
                boolean[][] got = MessTable.find(n, p[0], p[1]);
                boolean want = bruteExists(n, p[0], p[1]);
                assertThat(got.length == n).isEqualTo(want);
                if (want) {
                    assertThat(MessTable.isPeaceful(got, p[0], p[1])).isTrue();
                }
            }
        }
    }

    @Test
    void knownRamseyNumbers() {
        assertThat(MessTable.ramsey(3, 3)).isEqualTo(6);
        assertThat(MessTable.ramsey(3, 4)).isEqualTo(9);
        assertThat(MessTable.ramsey(2, 4)).isEqualTo(4);
        assertThat(MessTable.ramsey(3, 2)).isEqualTo(3);
    }

    @Test
    void questAndGuards() {
        assertThat(MessTable.QUEST_ID).isEqualTo("q_mess_table");
        boolean[][] pentagon = new boolean[5][5];
        for (int i = 0; i < 5; i++) {
            pentagon[i][(i + 1) % 5] = true;
            pentagon[(i + 1) % 5][i] = true;
        }
        assertThat(MessTable.quest(5, pentagon)).isTrue();
        assertThat(MessTable.quest(5, new boolean[5][5])).isFalse();
        assertThatThrownBy(() -> MessTable.ramsey(4, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> MessTable.find(11, 3, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}