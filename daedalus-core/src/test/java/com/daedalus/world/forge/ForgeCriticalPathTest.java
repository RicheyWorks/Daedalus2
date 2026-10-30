// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeCriticalPath.Grade;
import com.daedalus.world.forge.ForgeCriticalPath.Schedule;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ForgeCriticalPathTest {

    /** Brute force: the longest path ending at each job, by depth-first search over every path. */
    private static int longestThrough(int[] d, int[][] e, int j) {
        int best = d[j];
        for (int[] x : e) {
            if (x[0] == j) {
                best = Math.max(best, d[j] + longestThrough(d, e, x[1]));
            }
        }
        return best;
    }

    private static int bruteMakespan(int[] d, int[][] e) {
        int m = 0;
        for (int j = 0; j < d.length; j++) {
            m = Math.max(m, longestThrough(d, e, j));
        }
        return m;
    }

    @Test
    void makespanAndSlackMatchBruteForceOnSeededRefits() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = 1 + (int) (seed % 11);
            int[] d = ForgeCriticalPath.refitDurations(seed, n);
            int[][] e = ForgeCriticalPath.refitEdges(seed, n, 30);
            Schedule s = ForgeCriticalPath.schedule(d, e);
            assertThat(s.cyclic()).isFalse();
            int m = bruteMakespan(d, e);
            assertThat(s.makespan()).as("seed %d", seed).isEqualTo(m);
            for (int j = 0; j < n; j++) {
                // longest path through j = (longest path ending before j) + longest from j
                int head = s.earliest().get(j);
                int through = head + longestThrough(d, e, j);
                assertThat(s.slack(j)).isEqualTo(m - through);
                assertThat(s.slack(j)).isGreaterThanOrEqualTo(0);
            }
        }
    }

    @Test
    void orderRespectsEveryLinkAndCriticalPathIsAZeroSlackChainOfFullLength() {
        for (long seed = 1; seed <= 200; seed++) {
            int n = 2 + (int) (seed % 10);
            int[] d = ForgeCriticalPath.refitDurations(seed, n);
            int[][] e = ForgeCriticalPath.refitEdges(seed, n, 40);
            Schedule s = ForgeCriticalPath.schedule(d, e);
            for (int[] x : e) {
                assertThat(s.order().indexOf(x[0])).isLessThan(s.order().indexOf(x[1]));
                assertThat(s.earliest().get(x[1])).isGreaterThanOrEqualTo(s.earliest().get(x[0]) + d[x[0]]);
            }
            int len = 0;
            for (int j : s.critical()) {
                assertThat(s.slack(j)).isZero();
                len += d[j];
            }
            assertThat(len).isEqualTo(s.makespan());
        }
    }

    @Test
    void handWorkedRefit() {
        int[] d = {3, 2, 4, 1};
        int[][] e = {{0, 1}, {0, 2}, {1, 3}, {2, 3}};
        Schedule s = ForgeCriticalPath.schedule(d, e);
        assertThat(s.makespan()).isEqualTo(8);
        assertThat(s.critical()).containsExactly(0, 2, 3);
        assertThat(s.slack(1)).isEqualTo(2);
        assertThat(ForgeCriticalPath.grade(s, 8)).isEqualTo(Grade.ON_TIME);
        assertThat(ForgeCriticalPath.grade(s, 7)).isEqualTo(Grade.LATE);
        assertThat(ForgeCriticalPath.forgemasterLine(s, 7)).contains("day 8");
    }

    @Test
    void cyclesAreReported() {
        Schedule s = ForgeCriticalPath.schedule(new int[] {1, 1, 1}, new int[][] {{0, 1}, {1, 2}, {2, 1}});
        assertThat(s.cyclic()).isTrue();
        assertThat(ForgeCriticalPath.grade(s, 3)).isEqualTo(Grade.CYCLE);
        assertThat(ForgeCriticalPath.forgemasterLine(s, 3)).contains("ring");
    }

    @Test
    void sameSeedReplays() {
        assertThat(ForgeCriticalPath.refitDurations(193L, 9)).isEqualTo(ForgeCriticalPath.refitDurations(193L, 9));
        assertThat(ForgeCriticalPath.refitEdges(193L, 9, 30)).isDeepEqualTo(ForgeCriticalPath.refitEdges(193L, 9, 30));
        assertThat(ForgeCriticalPath.schedule(ForgeCriticalPath.refitDurations(193L, 9),
                ForgeCriticalPath.refitEdges(193L, 9, 30))).isEqualTo(ForgeCriticalPath.schedule(
                ForgeCriticalPath.refitDurations(193L, 9), ForgeCriticalPath.refitEdges(193L, 9, 30)));
        assertThat(ForgeCriticalPath.QUEST_ID).isEqualTo("q_forge_critical_path");
    }

    @Test
    void edgeCasesAndRejects() {
        Schedule empty = ForgeCriticalPath.schedule(new int[0], new int[0][]);
        assertThat(empty.makespan()).isZero();
        assertThat(empty.critical()).isEmpty();
        assertThatThrownBy(() -> ForgeCriticalPath.schedule(new int[] {1}, new int[][] {{0, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ForgeCriticalPath.schedule(new int[] {-1}, new int[0][]))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
