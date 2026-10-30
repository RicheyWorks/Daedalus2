// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ChalkGridTest {

    /** Checks every k-cell segment in all eight directions. */
    private static boolean brute(int m, int n, int k, int[] b, int who) {
        for (int r = 0; r < m; r++) {
            for (int c = 0; c < n; c++) {
                for (int dr = -1; dr <= 1; dr++) {
                    for (int dc = -1; dc <= 1; dc++) {
                        if (dr == 0 && dc == 0) {
                            continue;
                        }
                        int er = r + dr * (k - 1);
                        int ec = c + dc * (k - 1);
                        if (er < 0 || ec < 0 || er >= m || ec >= n) {
                            continue;
                        }
                        boolean all = true;
                        for (int i = 0; i < k && all; i++) {
                            all = b[(r + dr * i) * n + c + dc * i] == who;
                        }
                        if (all) {
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    /** Plain minimax, no memo, using the brute line check. */
    private static int plain(int m, int n, int k, boolean misere, int[] b, int who) {
        int best = -2;
        for (int i = 0; i < b.length; i++) {
            if (b[i] == 0) {
                b[i] = who;
                int v;
                if (brute(m, n, k, b, who)) {
                    v = misere ? -1 : 1;
                } else {
                    v = -plain(m, n, k, misere, b, 3 - who);
                }
                b[i] = 0;
                best = Math.max(best, v);
            }
        }
        return best == -2 ? 0 : best;
    }

    @Test
    void lineMatchesBrute() {
        SplittableRandom rnd = new SplittableRandom(421);
        for (int t = 0; t < 3000; t++) {
            int m = 1 + rnd.nextInt(8);
            int n = 1 + rnd.nextInt(8);
            int k = 3 + rnd.nextInt(3);
            int[] b = new int[m * n];
            for (int i = 0; i < b.length; i++) {
                b[i] = rnd.nextInt(5) == 0 ? 1 : 0;
            }
            assertThat(new ChalkGrid(m, n, k, false).lineOwner(b) == 1).isEqualTo(brute(m, n, k, b, 1));
        }
    }

    @Test
    void solverMatchesPlainMinimax() {
        SplittableRandom rnd = new SplittableRandom(4210);
        int[][] sizes = {{3, 3}, {3, 4}, {4, 3}, {2, 5}};
        for (int[] s : sizes) {
            for (boolean mis : new boolean[] {false, true}) {
                ChalkGrid g = new ChalkGrid(s[0], s[1], 3, mis);
                for (int t = 0; t < 10; t++) {
                    int[] b = new int[s[0] * s[1]];
                    int who = 1;
                    int pre = s[0] * s[1] == 9 && t < 2 ? 0 : 2 + rnd.nextInt(4);
                    for (int p = 0; p < pre; p++) {
                        int i = rnd.nextInt(b.length);
                        if (b[i] == 0) {
                            b[i] = who;
                            who = 3 - who;
                        }
                    }
                    if (g.lineOwner(b) != 0) {
                        continue;
                    }
                    assertThat(g.value(b, who)).isEqualTo(plain(s[0], s[1], 3, mis, b.clone(), who));
                }
            }
        }
    }

    @Test
    void classicThreeByThreeIsADrawAndReplays() {
        ChalkGrid g = new ChalkGrid(3, 3, 3, false);
        int[] b = new int[9];
        assertThat(g.value(b, 1)).isZero();
        int who = 1;
        for (int sq = g.bestSquare(b, who); sq >= 0; sq = g.bestSquare(b, who)) {
            b[sq] = who;
            who = 3 - who;
        }
        assertThat(g.lineOwner(b)).isZero();
        int[] fork = {1, 0, 0, 0, 2, 0, 0, 0, 1};
        assertThat(g.value(fork, 2)).isEqualTo(plain(3, 3, 3, false, fork.clone(), 2));
    }

    @Test
    void questAndBounds() {
        int v = new ChalkGrid(3, 3, 3, true).value(new int[9], 1);
        assertThat(v).isEqualTo(plain(3, 3, 3, true, new int[9], 1));
        assertThat(ChalkGrid.quest(v)).isTrue();
        assertThat(ChalkGrid.quest(v == 1 ? 0 : 1)).isFalse();
        assertThat(ChalkGrid.QUEST_ID).isEqualTo("q_chalk_grid");
        assertThatThrownBy(() -> new ChalkGrid(9, 3, 3, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ChalkGrid(3, 3, 6, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ChalkGrid(4, 4, 3, false).value(new int[16], 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ChalkGrid(3, 3, 3, false).lineOwner(new int[8])).isInstanceOf(IllegalArgumentException.class);
    }
}