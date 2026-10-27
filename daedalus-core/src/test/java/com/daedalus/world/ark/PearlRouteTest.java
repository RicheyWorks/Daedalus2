// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class PearlRouteTest {

    private static long brute(int[][] pearls) {
        int e = PearlRoute.edgeCount(pearls.length, pearls[0].length);
        long n = 0;
        boolean[] on = new boolean[e];
        for (int mask = 0; mask < (1 << e); mask++) {
            for (int i = 0; i < e; i++) {
                on[i] = (mask >> i & 1) != 0;
            }
            if (PearlRoute.isValid(pearls, on)) {
                n++;
            }
        }
        return n;
    }

    @Test
    void countMatchesBruteForceOverEveryEdgeSubset() {
        SplittableRandom rnd = new SplittableRandom(386);
        int[][] sizes = {{2, 2}, {2, 3}, {3, 3}, {3, 4}, {4, 3}, {2, 4}};
        int solvable = 0;
        for (int t = 0; t < 30; t++) {
            int[] s = sizes[t % sizes.length];
            int[][] p = new int[s[0]][s[1]];
            int k = t < sizes.length ? 0 : rnd.nextInt(1, 4);
            for (int i = 0; i < k; i++) {
                p[rnd.nextInt(s[0])][rnd.nextInt(s[1])] = rnd.nextInt(1, 3);
            }
            long want = brute(p);
            if (want > 0) {
                solvable++;
            }
            assertThat(PearlRoute.count(p, Long.MAX_VALUE)).as("t%d", t).isEqualTo(want);
            assertThat(PearlRoute.solve(p).length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isGreaterThan(6);
    }

    @Test
    void knownCycleCountsAndFourByFive() {
        assertThat(PearlRoute.count(new int[2][2], 100)).isEqualTo(1);
        assertThat(PearlRoute.count(new int[3][3], 100)).isEqualTo(13);
        int[][] p = {
            {0, 0, 0, 0, 0},
            {0, 2, 0, 1, 0},
            {0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0}};
        boolean[] s = PearlRoute.solve(p);
        assertThat(s).hasSize(PearlRoute.edgeCount(4, 5));
        assertThat(PearlRoute.quest(p, s)).isTrue();
        assertThat(PearlRoute.quest(p, new boolean[s.length])).isFalse();
        assertThat(PearlRoute.QUEST_ID).isEqualTo("q_pearl_route");
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> PearlRoute.count(new int[5][5], 1))
            .isInstanceOf(IllegalArgumentException.class);
        assertThat(PearlRoute.count(new int[][] {{1}}, 5)).isZero();
    }
}