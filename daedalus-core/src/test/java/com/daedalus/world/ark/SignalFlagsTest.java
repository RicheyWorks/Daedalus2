// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SignalFlagsTest {

    private static int[][] blank(int n) {
        int[][] g = new int[n][n];
        for (int[] row : g) {
            Arrays.fill(row, -1);
        }
        return g;
    }

    private static long bruteCells(int[][] givens) {
        int n = givens.length;
        long found = 0;
        int[][] b = new int[n][n];
        for (int mask = 0; mask < (1 << (n * n)); mask++) {
            for (int i = 0; i < n * n; i++) {
                b[i / n][i % n] = mask >> i & 1;
            }
            if (SignalFlags.isValid(givens, b)) {
                found++;
            }
        }
        return found;
    }

    /** Independent 6x6 total: every 6-tuple of rows, checked only with isValid. */
    private static long bruteRows6() {
        int[][] rows = new int[64][];
        int k = 0;
        for (int m = 0; m < 64; m++) {
            int[] row = new int[6];
            for (int i = 0; i < 6; i++) {
                row[i] = m >> i & 1;
            }
            if (Integer.bitCount(m) == 3 && (m & 7) != 7 && (m & 14) != 14 && (m & 28) != 28
                && (m & 56) != 56 && (m & 7) != 0 && (m & 14) != 0 && (m & 28) != 0
                && (m & 56) != 0) {
                rows[k++] = row;
            }
        }
        int[][] g = blank(6);
        int[][] b = new int[6][];
        long found = 0;
        int[] idx = new int[6];
        long total = 1;
        for (int i = 0; i < 6; i++) {
            total *= k;
        }
        for (long code = 0; code < total; code++) {
            long x = code;
            for (int i = 0; i < 6; i++) {
                idx[i] = (int) (x % k);
                x /= k;
            }
            for (int i = 0; i < 6; i++) {
                b[i] = rows[idx[i]];
            }
            if (SignalFlags.isValid(g, b)) {
                found++;
            }
        }
        return found;
    }

    @Test
    void countMatchesBruteForceUpToFour() {
        assertThat(SignalFlags.count(blank(2), 100)).isEqualTo(bruteCells(blank(2)));
        assertThat(SignalFlags.count(blank(4), 1000)).isEqualTo(bruteCells(blank(4)));
        SplittableRandom rnd = new SplittableRandom(392);
        for (int t = 0; t < 30; t++) {
            int[][] g = blank(4);
            int k = rnd.nextInt(1, 6);
            for (int i = 0; i < k; i++) {
                g[rnd.nextInt(4)][rnd.nextInt(4)] = rnd.nextInt(2);
            }
            long want = bruteCells(g);
            assertThat(SignalFlags.count(g, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            assertThat(SignalFlags.solve(g).length == 0).isEqualTo(want == 0);
        }
    }

    @Test
    void sixBySixTotalMatchesRowBruteForce() {
        assertThat(SignalFlags.count(blank(6), Long.MAX_VALUE)).isEqualTo(bruteRows6());
    }

    @Test
    void solveAndQuest() {
        int[][] g = blank(6);
        g[0][0] = 1;
        g[2][3] = 0;
        g[5][5] = 1;
        int[][] s = SignalFlags.solve(g);
        assertThat(s).hasNumberOfRows(6);
        assertThat(SignalFlags.quest(g, s)).isTrue();
        int[][] bad = new int[6][];
        for (int r = 0; r < 6; r++) {
            bad[r] = s[r].clone();
        }
        bad[0][0] = 0;
        assertThat(SignalFlags.quest(g, bad)).isFalse();
        assertThat(SignalFlags.QUEST_ID).isEqualTo("q_signal_flags");
        assertThatThrownBy(() -> SignalFlags.count(blank(5), 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}