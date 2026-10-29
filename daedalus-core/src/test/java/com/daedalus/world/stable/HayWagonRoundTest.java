// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.HayWagonRound.Round;
import com.daedalus.world.stable.HayWagonRound.Yard;

import org.junit.jupiter.api.Test;

class HayWagonRoundTest {

    @Test
    void bestMatchesBruteForceOverEveryOrder() {
        for (long seed = 1; seed <= 300; seed++) {
            int stalls = (int) (seed % 8);
            Yard yard = HayWagonRound.yard(seed, stalls, 10, 4);
            Round r = HayWagonRound.best(yard);
            assertThat(r.finish()).as("seed %d", seed).isEqualTo(brute(yard));
            assertThat(r.finish()).isNotEqualTo(HayWagonRound.INFEASIBLE);
            assertThat(HayWagonRound.drive(yard, r.order())).isEqualTo(r.finish());
            assertThat(HayWagonRound.quest(yard, r.order())).isTrue();
        }
    }

    @Test
    void nearestIsNeverBetterAndSometimesLateOrStranded() {
        int worse = 0;
        for (long seed = 1; seed <= 300; seed++) {
            Yard yard = HayWagonRound.yard(seed, 9, 10, 4);
            Round b = HayWagonRound.best(yard);
            Round g = HayWagonRound.nearest(yard);
            if (g.finish() == HayWagonRound.INFEASIBLE) {
                worse++;
                continue;
            }
            assertThat(HayWagonRound.drive(yard, g.order())).isEqualTo(g.finish());
            assertThat(g.finish()).isGreaterThanOrEqualTo(b.finish());
            if (g.finish() > b.finish()) {
                worse++;
            }
        }
        assertThat(worse).isPositive();
    }

    @Test
    void stallByTheBarnStrandsTheNearestHabit() {
        // Barn at 2. Stall 2 sits at the barn but opens at 7; stall 1 (at 1) closes at 7 and
        // stall 3 (at 3) closes at 5. Nearest feeds stall 2 first, waits to 7, and misses stall 1.
        // Best: 3 (t=1), 1 (t=3, wait to 6), 2 (t=7), home at 7.
        Yard yard = new Yard(new int[] {2, 1, 2, 3}, new int[4], new int[] {0, 6, 7, 0},
                new int[] {99, 7, 12, 5});
        assertThat(HayWagonRound.nearest(yard).finish()).isEqualTo(HayWagonRound.INFEASIBLE);
        assertThat(HayWagonRound.best(yard)).isEqualTo(new Round(7, new int[] {3, 1, 2}));
        assertThat(HayWagonRound.quest(yard, new int[] {2, 1, 3})).isFalse();
    }

    @Test
    void badRoundsAreInfeasible() {
        Yard yard = new Yard(new int[] {0, 2, 4}, new int[3], new int[] {0, 0, 0}, new int[] {99, 2, 4});
        assertThat(HayWagonRound.drive(yard, new int[] {1, 2})).isEqualTo(8);
        assertThat(HayWagonRound.drive(yard, new int[] {2, 1})).isEqualTo(HayWagonRound.INFEASIBLE);
        assertThat(HayWagonRound.drive(yard, new int[] {1, 1})).isEqualTo(HayWagonRound.INFEASIBLE);
        assertThat(HayWagonRound.drive(yard, new int[] {1})).isEqualTo(HayWagonRound.INFEASIBLE);
        assertThat(HayWagonRound.drive(yard, new int[] {0, 3})).isEqualTo(HayWagonRound.INFEASIBLE);
        Yard shut = new Yard(new int[] {0, 5}, new int[2], new int[] {0, 0}, new int[] {99, 4});
        assertThat(HayWagonRound.best(shut).finish()).isEqualTo(HayWagonRound.INFEASIBLE);
        assertThat(HayWagonRound.best(new Yard(new int[1], new int[1], new int[1], new int[1])).finish()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(HayWagonRound.yard(7, 6, 9, 3)).isEqualTo(HayWagonRound.yard(7, 6, 9, 3));
        assertThat(HayWagonRound.QUEST_ID).isEqualTo("q_hay_on_time");
        assertThatThrownBy(() -> HayWagonRound.yard(1, 13, 9, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Yard(new int[] {0, 1}, new int[2], new int[] {0, 5}, new int[] {9, 4}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Yard(new int[0], new int[0], new int[0], new int[0]))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(Yard yard) {
        int m = yard.stalls();
        int[] order = new int[m];
        for (int i = 0; i < m; i++) {
            order[i] = i + 1;
        }
        return permute(yard, order, 0);
    }

    private static int permute(Yard yard, int[] order, int k) {
        if (k == order.length) {
            return HayWagonRound.drive(yard, order);
        }
        int best = HayWagonRound.INFEASIBLE;
        for (int i = k; i < order.length; i++) {
            swap(order, k, i);
            int f = permute(yard, order, k + 1);
            if (f != HayWagonRound.INFEASIBLE && (best == HayWagonRound.INFEASIBLE || f < best)) {
                best = f;
            }
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
