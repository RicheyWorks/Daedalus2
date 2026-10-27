// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class HardtackBarTest {

    /** Plain recursion on a cell grid, no memo. */
    private static boolean plain(boolean[][] g) {
        for (int i = 0; i < g.length; i++) {
            for (int j = 0; j < g[0].length; j++) {
                if (g[i][j] && (i != 0 || j != 0)) {
                    boolean[][] h = new boolean[g.length][];
                    for (int r = 0; r < g.length; r++) {
                        h[r] = g[r].clone();
                        for (int c = 0; c < g[0].length; c++) {
                            if (r >= i && c >= j) {
                                h[r][c] = false;
                            }
                        }
                    }
                    if (!plain(h)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    @Test
    void matchesPlainRecursion() {
        HardtackBar h = new HardtackBar();
        for (int a = 1; a <= 4; a++) {
            for (int b = 0; b <= a; b++) {
                for (int c = 0; c <= b; c++) {
                    for (int d = 0; d <= c; d++) {
                        int[] s = {a, b, c, d};
                        boolean[][] g = new boolean[4][4];
                        for (int r = 0; r < 4; r++) {
                            for (int col = 0; col < s[r]; col++) {
                                g[r][col] = true;
                            }
                        }
                        assertThat(h.wins(s)).as("%d %d %d %d", s[0], s[1], s[2], s[3]).isEqualTo(plain(g));
                    }
                }
            }
        }
    }

    @Test
    void everyBarBiggerThanOneIsAFirstWin() {
        HardtackBar h = new HardtackBar();
        assertThat(h.wins(HardtackBar.bar(1, 1))).isFalse();
        for (int r = 1; r <= 7; r++) {
            for (int c = 1; c <= 7; c++) {
                if (r * c > 1) {
                    int[] s = HardtackBar.bar(r, c);
                    assertThat(h.wins(s)).isTrue();
                    int[] mv = h.winningBite(s);
                    assertThat(h.wins(HardtackBar.bite(s, mv[0], mv[1]))).isFalse();
                }
            }
        }
    }

    @Test
    void knownWinningBitesLose() {
        HardtackBar h = new HardtackBar();
        for (int n = 2; n <= 8; n++) {
            assertThat(h.wins(HardtackBar.bite(HardtackBar.bar(n, n), 1, 1))).as("square %d", n).isFalse();
            assertThat(h.wins(HardtackBar.bite(HardtackBar.bar(2, n), 1, n - 1))).as("two rows %d", n).isFalse();
            assertThat(h.wins(HardtackBar.bite(HardtackBar.bar(1, n), 0, 1))).isFalse();
        }
        assertThat(h.winningBite(new int[] {1})).isEmpty();
    }

    @Test
    void questAndBounds() {
        assertThat(HardtackBar.quest(3, 4, true)).isTrue();
        assertThat(HardtackBar.quest(1, 1, true)).isFalse();
        assertThat(HardtackBar.QUEST_ID).isEqualTo("q_hardtack_bar");
        assertThatThrownBy(() -> HardtackBar.bar(11, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HardtackBar().wins(new int[] {2, 3})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HardtackBar.bite(new int[] {2}, 0, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HardtackBar().wins(new int[] {0})).isInstanceOf(IllegalArgumentException.class);
    }
}