// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.FarriersTwoAnvils.Plan;

import org.junit.jupiter.api.Test;

class FarriersTwoAnvilsTest {

    @Test
    void bestMatchesBruteForceAndIsLegal() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 7);
            int[] p = FarriersTwoAnvils.durations(seed, n);
            int[] q = FarriersTwoAnvils.links(seed, n, 30);
            Plan b = FarriersTwoAnvils.best(p, q);
            assertThat(b.makespan()).as("seed %d", seed).isEqualTo(brute(p, q));
            assertThat(FarriersTwoAnvils.finish(p, q, b.start(), b.anvil())).isEqualTo(b.makespan());
            assertThat(FarriersTwoAnvils.quest(p, q, b.start(), b.anvil())).isTrue();
        }
    }

    @Test
    void listScheduleIsLegalNeverBetterAndSometimesLater() {
        int later = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] p = FarriersTwoAnvils.durations(seed, 8);
            int[] q = FarriersTwoAnvils.links(seed, 8, 25);
            Plan g = FarriersTwoAnvils.listSchedule(p, q);
            Plan b = FarriersTwoAnvils.best(p, q);
            assertThat(FarriersTwoAnvils.finish(p, q, g.start(), g.anvil())).isEqualTo(g.makespan());
            assertThat(g.makespan()).isGreaterThanOrEqualTo(b.makespan());
            if (g.makespan() > b.makespan()) {
                later++;
            }
        }
        assertThat(later).isPositive();
    }

    @Test
    void lowestNumberFirstFinishesLate() {
        // Jobs 2, 3 and 4 long. In job order the two short ones go first and the 4 waits: done at 6.
        // Best puts the 4 on its own anvil and the 2 then 3 on the other: done at 5.
        int[] p = {2, 3, 4};
        int[] q = new int[3];
        assertThat(FarriersTwoAnvils.listSchedule(p, q).makespan()).isEqualTo(6);
        assertThat(FarriersTwoAnvils.best(p, q).makespan()).isEqualTo(5);
        Plan g = FarriersTwoAnvils.listSchedule(p, q);
        assertThat(FarriersTwoAnvils.quest(p, q, g.start(), g.anvil())).isFalse();
    }

    @Test
    void brokenSchedulesAreInvalid() {
        int[] p = {2, 3};
        int[] q = {0, 1};
        assertThat(FarriersTwoAnvils.finish(p, q, new int[] {0, 2}, new int[] {0, 1})).isEqualTo(5);
        assertThat(FarriersTwoAnvils.finish(p, q, new int[] {0, 1}, new int[] {0, 1})).isEqualTo(FarriersTwoAnvils.INVALID);
        int[] free = new int[2];
        assertThat(FarriersTwoAnvils.finish(p, free, new int[] {0, 1}, new int[] {0, 0})).isEqualTo(FarriersTwoAnvils.INVALID);
        assertThat(FarriersTwoAnvils.finish(p, free, new int[] {0, 0}, new int[] {0, 2})).isEqualTo(FarriersTwoAnvils.INVALID);
        assertThat(FarriersTwoAnvils.finish(p, free, new int[] {-1, 0}, new int[] {0, 1})).isEqualTo(FarriersTwoAnvils.INVALID);
        assertThat(FarriersTwoAnvils.finish(p, free, new int[] {0}, new int[] {0})).isEqualTo(FarriersTwoAnvils.INVALID);
        assertThat(FarriersTwoAnvils.best(new int[0], new int[0]).makespan()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(FarriersTwoAnvils.durations(3, 7)).containsExactly(FarriersTwoAnvils.durations(3, 7));
        assertThat(FarriersTwoAnvils.links(3, 7, 40)).containsExactly(FarriersTwoAnvils.links(3, 7, 40));
        assertThat(FarriersTwoAnvils.QUEST_ID).isEqualTo("q_two_anvils");
        assertThatThrownBy(() -> FarriersTwoAnvils.durations(1, 11)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FarriersTwoAnvils.best(new int[] {10}, new int[] {0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FarriersTwoAnvils.best(new int[] {1, 1}, new int[] {2, 0})).isInstanceOf(IllegalArgumentException.class);
    }

    /** Every topological order times every anvil assignment, each job as early as its links and anvil allow. */
    private static int brute(int[] p, int[] q) {
        int n = p.length;
        if (n == 0) {
            return 0;
        }
        int[] order = new int[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        return permute(p, q, order, 0);
    }

    private static int permute(int[] p, int[] q, int[] order, int k) {
        int n = order.length;
        if (k == n) {
            int[] pos = new int[n];
            for (int i = 0; i < n; i++) {
                pos[order[i]] = i;
            }
            for (int j = 0; j < n; j++) {
                for (int i = 0; i < n; i++) {
                    if ((q[j] & (1 << i)) != 0 && pos[i] > pos[j]) {
                        return Integer.MAX_VALUE;
                    }
                }
            }
            int best = Integer.MAX_VALUE;
            for (int mask = 0; mask < (1 << n); mask++) {
                int[] end = new int[n];
                int[] free = new int[2];
                int span = 0;
                for (int j : order) {
                    int a = (mask >> j) & 1;
                    int s = free[a];
                    for (int i = 0; i < n; i++) {
                        if ((q[j] & (1 << i)) != 0) {
                            s = Math.max(s, end[i]);
                        }
                    }
                    end[j] = s + p[j];
                    free[a] = end[j];
                    span = Math.max(span, end[j]);
                }
                best = Math.min(best, span);
            }
            return best;
        }
        int best = Integer.MAX_VALUE;
        for (int i = k; i < n; i++) {
            swap(order, k, i);
            best = Math.min(best, permute(p, q, order, k + 1));
            swap(order, k, i);
        }
        return best;
    }

    private static void swap(int[] a, int i, int j) {
        int t = a[i];
        a[i] = a[j];
        a[j] = t;
    }
}
