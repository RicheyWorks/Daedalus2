// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class HammockRowsTest {

    /** Scans every k-cell segment in every direction, cell by cell. */
    private static int brute(int w, int h, int k, int[] b) {
        int found = 0;
        int[][] dirs = {{1, 0}, {0, 1}, {1, 1}, {1, -1}, {-1, 0}, {0, -1}, {-1, -1}, {-1, 1}};
        for (int c = 0; c < w; c++) {
            for (int r = 0; r < h; r++) {
                for (int[] d : dirs) {
                    int ec = c + d[0] * (k - 1);
                    int er = r + d[1] * (k - 1);
                    if (ec < 0 || er < 0 || ec >= w || er >= h) {
                        continue;
                    }
                    int v = b[c * h + r];
                    boolean all = v != 0;
                    for (int i = 1; i < k && all; i++) {
                        all = b[(c + d[0] * i) * h + r + d[1] * i] == v;
                    }
                    if (all) {
                        found = v;
                    }
                }
            }
        }
        return found;
    }

    /** Plain minimax with no memo. */
    private static int plain(HammockRows g, int w, int h, int[] b, int who) {
        int best = -2;
        for (int c = 0; c < w; c++) {
            if (g.height(b, c) < 0) {
                continue;
            }
            int[] nb = g.drop(b, c, who);
            int v = g.winner(nb) == who ? 1 : -plain(g, w, h, nb, 3 - who);
            best = Math.max(best, v);
        }
        return best == -2 ? 0 : best;
    }

    private static int[] randomPlay(HammockRows g, int w, int h, int moves, SplittableRandom rnd) {
        int[] b = new int[w * h];
        int who = 1;
        for (int m = 0; m < moves; m++) {
            int c = rnd.nextInt(w);
            if (g.height(b, c) >= 0) {
                b = g.drop(b, c, who);
                who = 3 - who;
            }
        }
        return b;
    }

    @Test
    void winnerMatchesBruteScan() {
        SplittableRandom rnd = new SplittableRandom(416);
        for (int t = 0; t < 2000; t++) {
            int w = 1 + rnd.nextInt(10);
            int h = 1 + rnd.nextInt(10);
            int k = 3 + rnd.nextInt(4);
            HammockRows g = new HammockRows(w, h, k);
            int[] b = randomPlay(g, w, h, rnd.nextInt(w * h + 1), rnd);
            boolean one = brute(w, h, k, b) != 0;
            assertThat(g.winner(b) != 0).isEqualTo(one);
        }
    }

    @Test
    void solverMatchesPlainMinimax() {
        SplittableRandom rnd = new SplittableRandom(4160);
        int[][] racks = {{3, 3, 3}, {4, 3, 3}, {3, 4, 3}, {4, 4, 3}, {4, 4, 4}, {5, 3, 3}};
        for (int[] rk : racks) {
            HammockRows g = new HammockRows(rk[0], rk[1], rk[2]);
            for (int t = 0; t < 15; t++) {
                int[] b = randomPlay(g, rk[0], rk[1], t < 3 && rk[0] * rk[1] <= 12 ? 0 : 5 + rnd.nextInt(5), rnd);
                if (g.winner(b) != 0) {
                    continue;
                }
                int filled = 0;
                for (int v : b) {
                    filled += v == 0 ? 0 : 1;
                }
                int who = (filled & 1) == 0 ? 1 : 2;
                assertThat(g.value(b, who)).isEqualTo(plain(g, rk[0], rk[1], b, who));
            }
        }
    }

    @Test
    void bestPlayReplaysToItsValue() {
        HammockRows g = new HammockRows(4, 4, 3);
        int[] b = new int[16];
        int start = g.value(b, 1);
        int who = 1;
        while (g.winner(b) == 0 && g.bestColumn(b, who) >= 0) {
            b = g.drop(b, g.bestColumn(b, who), who);
            who = 3 - who;
        }
        int result = g.winner(b) == 0 ? 0 : g.winner(b) == 1 ? 1 : -1;
        assertThat(result).isEqualTo(start);
        assertThat(g.bestColumn(b, who)).isEqualTo(-1);
    }

    @Test
    void questAndBounds() {
        int v = new HammockRows(4, 4, 3).value(new int[16], 1);
        assertThat(HammockRows.quest(v)).isTrue();
        assertThat(HammockRows.quest(v == 1 ? 0 : 1)).isFalse();
        assertThat(HammockRows.QUEST_ID).isEqualTo("q_hammock_rows");
        HammockRows g = new HammockRows(2, 2, 3);
        assertThatThrownBy(() -> g.drop(new int[] {1, 2, 0, 0}, 0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.winner(new int[] {0, 1, 0, 0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HammockRows(11, 2, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HammockRows(5, 4, 3).value(new int[20], 1)).isInstanceOf(IllegalArgumentException.class);
    }
}