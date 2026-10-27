// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CablePairsTest {

    private static long brute(int[][] s, int k) {
        int rows = s.length;
        int cols = s[0].length;
        int n = rows * cols;
        long total = 1;
        for (int i = 0; i < n; i++) {
            total *= k;
        }
        long found = 0;
        int[][] g = new int[rows][cols];
        for (long code = 0; code < total; code++) {
            long x = code;
            for (int i = 0; i < n; i++) {
                g[i / cols][i % cols] = (int) (x % k) + 1;
                x /= k;
            }
            if (CablePairs.isValid(s, g)) {
                found++;
            }
        }
        return found;
    }

    @Test
    void countMatchesBruteForceOverEveryLabelling() {
        SplittableRandom rnd = new SplittableRandom(389);
        int solvable = 0;
        for (int t = 0; t < 60; t++) {
            int rows = rnd.nextInt(1, 4);
            int cols = rnd.nextInt(2, 4);
            int n = rows * cols;
            int k = n >= 6 && rnd.nextBoolean() ? 3 : 2;
            if (n < 2 * k) {
                k = n / 2;
            }
            int[][] s = new int[rows][cols];
            for (int label = 1; label <= k; label++) {
                for (int rep = 0; rep < 2; rep++) {
                    int cell;
                    do {
                        cell = rnd.nextInt(n);
                    } while (s[cell / cols][cell % cols] != 0);
                    s[cell / cols][cell % cols] = label;
                }
            }
            long want = brute(s, k);
            if (want > 0) {
                solvable++;
            }
            assertThat(CablePairs.count(s, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            int[][] sol = CablePairs.solve(s);
            assertThat(sol.length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isGreaterThan(5);
    }

    @Test
    void solvesFourByFourAndQuest() {
        int[][] s = {
            {1, 0, 0, 0},
            {2, 0, 0, 0},
            {0, 3, 0, 0},
            {3, 2, 0, 1}};
        int[][] sol = CablePairs.solve(s);
        assertThat(sol).hasNumberOfRows(4);
        assertThat(CablePairs.quest(s, sol)).isTrue();
        int[][] bad = new int[4][];
        for (int r = 0; r < 4; r++) {
            bad[r] = sol[r].clone();
        }
        bad[1][1] = bad[1][1] == 1 ? 2 : 1;
        assertThat(CablePairs.quest(s, bad)).isFalse();
        assertThat(CablePairs.QUEST_ID).isEqualTo("q_cable_pairs");
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> CablePairs.count(new int[][] {{1, 0, 0}}, 1))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CablePairs.count(new int[5][2], 1))
            .isInstanceOf(IllegalArgumentException.class);
        assertThat(CablePairs.count(new int[][] {{1, 2, 1, 2}}, 5)).isZero();
        assertThat(CablePairs.count(new int[][] {{1, 0, 1}}, 5)).isEqualTo(1);
    }
}