// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayDeque;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SignalWebTest {

    /** Flood fill from crew's first edge using the six hex neighbours. */
    private static boolean flood(int n, int[] b, int who) {
        boolean[] seen = new boolean[n * n];
        ArrayDeque<Integer> q = new ArrayDeque<>();
        for (int k = 0; k < n; k++) {
            int i = who == 1 ? k : k * n;
            if (b[i] == who) {
                seen[i] = true;
                q.add(i);
            }
        }
        int[][] nb = {{0, -1}, {0, 1}, {-1, 0}, {1, 0}, {-1, 1}, {1, -1}};
        while (!q.isEmpty()) {
            int i = q.poll();
            int r = i / n;
            int c = i % n;
            if ((who == 1 ? r : c) == n - 1) {
                return true;
            }
            for (int[] d : nb) {
                int rr = r + d[0];
                int cc = c + d[1];
                if (rr >= 0 && cc >= 0 && rr < n && cc < n && !seen[rr * n + cc] && b[rr * n + cc] == who) {
                    seen[rr * n + cc] = true;
                    q.add(rr * n + cc);
                }
            }
        }
        return false;
    }

    @Test
    void winnerMatchesFloodFill() {
        SplittableRandom rnd = new SplittableRandom(413);
        for (int t = 0; t < 3000; t++) {
            int n = 1 + rnd.nextInt(11);
            int[] b = new int[n * n];
            for (int i = 0; i < b.length; i++) {
                b[i] = rnd.nextInt(3);
            }
            int w = SignalWeb.winner(n, b);
            int want = flood(n, b, 1) ? 1 : flood(n, b, 2) ? 2 : 0;
            assertThat(w).isEqualTo(want);
        }
    }

    @Test
    void everyFullBoardHasExactlyOneWinner() {
        for (int n = 1; n <= 4; n++) {
            int size = n * n;
            for (int mask = 0; mask < 1 << size; mask++) {
                int[] b = new int[size];
                for (int i = 0; i < size; i++) {
                    b[i] = (mask >> i & 1) != 0 ? 1 : 2;
                }
                assertThat(flood(n, b, 1)).as("n=%d mask=%d", n, mask).isNotEqualTo(flood(n, b, 2));
            }
        }
    }

    @Test
    void firstCrewWinsSmallBoards() {
        for (int n = 1; n <= 3; n++) {
            int[] empty = new int[n * n];
            assertThat(SignalWeb.wins(n, empty, 1)).isTrue();
            assertThat(SignalWeb.wins(n, empty, 2)).isTrue();
        }
        int[] b = new int[9];
        b[4] = 1;
        assertThat(SignalWeb.wins(3, b, 2)).isFalse();
        assertThat(SignalWeb.winningPost(3, b, 2)).isEqualTo(-1);
        b[0] = 2;
        int p = SignalWeb.winningPost(3, b, 1);
        assertThat(p).isNotNegative();
        b[p] = 1;
        assertThat(SignalWeb.wins(3, b, 2)).isFalse();
    }

    @Test
    void questAndBounds() {
        int[] b = {1, 2, 0, 1, 2, 0, 1, 0, 0};
        assertThat(SignalWeb.quest(3, b, 1)).isTrue();
        assertThat(SignalWeb.quest(3, b, 2)).isFalse();
        assertThat(SignalWeb.QUEST_ID).isEqualTo("q_signal_web");
        assertThat(SignalWeb.winningPost(3, b, 2)).isEqualTo(-1);
        assertThatThrownBy(() -> SignalWeb.winner(12, new int[144])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalWeb.winner(2, new int[] {0, 3, 0, 0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalWeb.wins(4, new int[16], 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalWeb.wins(2, new int[4], 3)).isInstanceOf(IllegalArgumentException.class);
    }
}