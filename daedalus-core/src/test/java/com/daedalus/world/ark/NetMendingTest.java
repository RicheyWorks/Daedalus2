// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class NetMendingTest {

    /** Brute mesh count from dot coordinates: each mesh needs its four sides. */
    private static int bruteClosed(int r, int c, boolean[] t) {
        int h = (r + 1) * c;
        int n = 0;
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                boolean top = t[i * c + j];
                boolean bottom = t[(i + 1) * c + j];
                boolean left = t[h + i * (c + 1) + j];
                boolean right = t[h + i * (c + 1) + j + 1];
                if (top && bottom && left && right) {
                    n++;
                }
            }
        }
        return n;
    }

    /** Plain minimax, no memo, scoring by recounting closed meshes. */
    private static int plain(NetMending net, int r, int c, boolean[] t) {
        int best = Integer.MIN_VALUE;
        for (int e = 0; e < t.length; e++) {
            if (!t[e]) {
                int before = bruteClosed(r, c, t);
                t[e] = true;
                int k = bruteClosed(r, c, t) - before;
                int v = k > 0 ? k + plain(net, r, c, t) : -plain(net, r, c, t);
                t[e] = false;
                best = Math.max(best, v);
            }
        }
        return best == Integer.MIN_VALUE ? 0 : best;
    }

    @Test
    void closedMatchesBruteOnRandomNets() {
        SplittableRandom rnd = new SplittableRandom(419);
        for (int t = 0; t < 2000; t++) {
            int r = 1 + rnd.nextInt(6);
            int c = 1 + rnd.nextInt(6);
            NetMending net = new NetMending(r, c);
            boolean[] tied = new boolean[net.edges()];
            for (int i = 0; i < tied.length; i++) {
                tied[i] = rnd.nextInt(4) != 0;
            }
            assertThat(net.closed(tied)).isEqualTo(bruteClosed(r, c, tied));
            for (int e = 0; e < tied.length; e++) {
                if (!tied[e]) {
                    int before = bruteClosed(r, c, tied);
                    tied[e] = true;
                    int after = bruteClosed(r, c, tied);
                    tied[e] = false;
                    assertThat(net.closes(tied, e)).isEqualTo(after - before);
                }
            }
        }
    }

    @Test
    void solverMatchesPlainMinimax() {
        SplittableRandom rnd = new SplittableRandom(4190);
        int[][] sizes = {{1, 1}, {1, 2}, {2, 1}, {1, 3}, {2, 2}};
        for (int[] s : sizes) {
            NetMending net = new NetMending(s[0], s[1]);
            for (int t = 0; t < 6; t++) {
                boolean[] tied = new boolean[net.edges()];
                int pre = s[0] * s[1] >= 3 ? 3 + rnd.nextInt(3) : t;
                for (int k = 0; k < pre && k < tied.length; k++) {
                    tied[rnd.nextInt(tied.length)] = true;
                }
                assertThat(net.margin(tied)).isEqualTo(plain(net, s[0], s[1], tied));
            }
        }
    }

    @Test
    void bestPlayReplaysToItsMargin() {
        NetMending net = new NetMending(2, 2);
        boolean[] tied = new boolean[net.edges()];
        int want = net.margin(tied);
        int[] score = new int[2];
        int who = 0;
        for (int e = net.bestCord(tied); e >= 0; e = net.bestCord(tied)) {
            int k = net.closes(tied, e);
            tied[e] = true;
            score[who] += k;
            if (k == 0) {
                who = 1 - who;
            }
        }
        assertThat(score[0] - score[1]).isEqualTo(want);
        assertThat(score[0] + score[1]).isEqualTo(4);
    }

    @Test
    void questAndBounds() {
        NetMending net = new NetMending(2, 2);
        int v = net.margin(new boolean[12]);
        assertThat(NetMending.quest(v)).isTrue();
        assertThat(NetMending.quest(v + 1)).isFalse();
        assertThat(NetMending.QUEST_ID).isEqualTo("q_net_mending");
        assertThat(new NetMending(6, 6).edges()).isEqualTo(84);
        assertThatThrownBy(() -> new NetMending(7, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new NetMending(3, 3).margin(new boolean[24])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> net.closes(new boolean[5], 0)).isInstanceOf(IllegalArgumentException.class);
    }
}