// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.BridleRackMatching.Pairing;

import org.junit.jupiter.api.Test;

class BridleRackMatchingTest {

    @Test
    void bestMatchesBruteForceOverEveryPairing() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 8);
            int[] t = BridleRackMatching.temperaments(seed, n);
            int[] s = BridleRackMatching.skills(seed, t);
            int[][] tm = BridleRackMatching.times(seed, n);
            Pairing b = BridleRackMatching.best(s, t, tm);
            assertThat(b.ready()).as("seed %d", seed).isEqualTo(brute(s, t, tm));
            assertThat(b.ready()).isNotEqualTo(BridleRackMatching.INFEASIBLE);
            assertThat(BridleRackMatching.ready(s, t, tm, b.groomOf())).isEqualTo(b.ready());
            assertThat(BridleRackMatching.quest(s, t, tm, b.groomOf())).isTrue();
        }
    }

    @Test
    void cheapestFirstIsNeverBetterAndSometimesLateOrStranded() {
        int worse = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] t = BridleRackMatching.temperaments(seed, 8);
            int[] s = BridleRackMatching.skills(seed, t);
            int[][] tm = BridleRackMatching.times(seed, 8);
            Pairing b = BridleRackMatching.best(s, t, tm);
            Pairing g = BridleRackMatching.cheapestFirst(s, t, tm);
            if (g.ready() == BridleRackMatching.INFEASIBLE) {
                worse++;
                continue;
            }
            assertThat(BridleRackMatching.ready(s, t, tm, g.groomOf())).isEqualTo(g.ready());
            assertThat(g.ready()).isGreaterThanOrEqualTo(b.ready());
            if (g.ready() > b.ready()) {
                worse++;
            }
        }
        assertThat(worse).isPositive();
    }

    @Test
    void quickPairsStrandOrDelayTheRide() {
        // The only groom skilled enough for the nervy horse 0 grabs calm horse 1 (5 min, the quickest
        // allowed pair), so horse 0 is left with nobody. Best: groom 0 on horse 0 (7), groom 1 on horse 1 (6).
        int[] skill = {2, 1};
        int[] temper = {2, 1};
        int[][] time = {{7, 5}, {2, 6}};
        assertThat(BridleRackMatching.cheapestFirst(skill, temper, time).ready()).isEqualTo(BridleRackMatching.INFEASIBLE);
        assertThat(BridleRackMatching.best(skill, temper, time)).isEqualTo(new Pairing(7, new int[] {0, 1}));
        // All compatible: the 1-minute pair first leaves a 9-minute pair; crossing both takes 2.
        int[] calm = {1, 1};
        int[][] slow = {{1, 2}, {2, 9}};
        assertThat(BridleRackMatching.cheapestFirst(calm, calm, slow).ready()).isEqualTo(9);
        assertThat(BridleRackMatching.best(calm, calm, slow)).isEqualTo(new Pairing(2, new int[] {1, 0}));
        assertThat(BridleRackMatching.quest(calm, calm, slow, new int[] {0, 1})).isFalse();
    }

    @Test
    void badPairingsAreInfeasible() {
        int[] skill = {2, 1};
        int[] temper = {2, 1};
        int[][] time = {{7, 5}, {2, 6}};
        assertThat(BridleRackMatching.ready(skill, temper, time, new int[] {1, 0})).isEqualTo(BridleRackMatching.INFEASIBLE);
        assertThat(BridleRackMatching.ready(skill, temper, time, new int[] {0, 0})).isEqualTo(BridleRackMatching.INFEASIBLE);
        assertThat(BridleRackMatching.ready(skill, temper, time, new int[] {0, 2})).isEqualTo(BridleRackMatching.INFEASIBLE);
        assertThat(BridleRackMatching.ready(skill, temper, time, new int[] {0})).isEqualTo(BridleRackMatching.INFEASIBLE);
        int[] weak = {1, 1};
        assertThat(BridleRackMatching.best(weak, temper, time).ready()).isEqualTo(BridleRackMatching.INFEASIBLE);
        assertThat(BridleRackMatching.best(new int[0], new int[0], new int[0][]).ready()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(BridleRackMatching.temperaments(5, 7)).containsExactly(BridleRackMatching.temperaments(5, 7));
        assertThat(BridleRackMatching.times(5, 4)).isDeepEqualTo(BridleRackMatching.times(5, 4));
        assertThat(BridleRackMatching.QUEST_ID).isEqualTo("q_all_tacked");
        assertThatThrownBy(() -> BridleRackMatching.temperaments(1, 11)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BridleRackMatching.best(new int[] {1}, new int[] {1}, new int[][] {{-1}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BridleRackMatching.best(new int[] {1}, new int[0], new int[][] {{1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(int[] s, int[] t, int[][] tm) {
        int n = s.length;
        int[] perm = new int[n];
        for (int i = 0; i < n; i++) {
            perm[i] = i;
        }
        return permute(s, t, tm, perm, 0);
    }

    private static int permute(int[] s, int[] t, int[][] tm, int[] perm, int k) {
        if (k == perm.length) {
            return BridleRackMatching.ready(s, t, tm, perm);
        }
        int best = BridleRackMatching.INFEASIBLE;
        for (int i = k; i < perm.length; i++) {
            swap(perm, k, i);
            int r = permute(s, t, tm, perm, k + 1);
            if (r != BridleRackMatching.INFEASIBLE && (best == BridleRackMatching.INFEASIBLE || r < best)) {
                best = r;
            }
            swap(perm, k, i);
        }
        return best;
    }

    private static void swap(int[] a, int i, int j) {
        int x = a[i];
        a[i] = a[j];
        a[j] = x;
    }
}
