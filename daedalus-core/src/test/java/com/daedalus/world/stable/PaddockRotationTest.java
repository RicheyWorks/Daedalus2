// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.PaddockRotation.Season;

import org.junit.jupiter.api.Test;

class PaddockRotationTest {

    @Test
    void bestMatchesBruteForceAndPlanEatsWhatItClaims() {
        for (long seed = 1; seed <= 300; seed++) {
            int m = 1 + (int) (seed % 3);
            int days = (int) (seed % 8);
            int[][] pk = PaddockRotation.paddocks(seed, m);
            Season s = PaddockRotation.best(pk[0], pk[1], days);
            assertThat(s.grass()).as("seed %d", seed).isEqualTo(brute(pk[0], pk[1], days));
            assertThat(s.plan()).hasSize(days);
            assertThat(PaddockRotation.graze(pk[0], pk[1], s.plan(), days)).isEqualTo(s.grass());
            assertThat(PaddockRotation.quest(pk[0], pk[1], s.plan(), days)).isTrue();
        }
    }

    @Test
    void greedyIsLegalNeverBetterAndSometimesWorse() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            int[][] pk = PaddockRotation.paddocks(seed, 4);
            Season g = PaddockRotation.greedy(pk[0], pk[1], 14);
            Season b = PaddockRotation.best(pk[0], pk[1], 14);
            assertThat(PaddockRotation.graze(pk[0], pk[1], g.plan(), 14)).isEqualTo(g.grass());
            assertThat(g.grass()).isLessThanOrEqualTo(b.grass());
            lost |= g.grass() < b.grass();
        }
        assertThat(lost).isTrue();
    }

    @Test
    void lettingTheLushPaddockRefillPaysOff() {
        int[] cap = CAP;
        int[] growth = GROWTH;
        Season g = PaddockRotation.greedy(cap, growth, DAYS);
        Season b = PaddockRotation.best(cap, growth, DAYS);
        assertThat(g.grass()).isEqualTo(8);
        assertThat(b.grass()).isEqualTo(9);
        assertThat(g.plan()).containsExactly(1, 0, 1, 0);
        assertThat(PaddockRotation.quest(cap, growth, g.plan(), DAYS)).isFalse();
        assertThat(PaddockRotation.quest(cap, growth, b.plan(), DAYS)).isTrue();
    }

    @Test
    void illegalPlansScoreMinusOne() {
        int[] cap = {4, 6};
        int[] growth = {2, 3};
        assertThat(PaddockRotation.graze(cap, growth, new int[] {0}, 2)).isEqualTo(-1);
        assertThat(PaddockRotation.graze(cap, growth, new int[] {0, 2}, 2)).isEqualTo(-1);
        assertThat(PaddockRotation.graze(cap, growth, new int[] {0, 0}, 2)).isEqualTo(4);
        assertThat(PaddockRotation.graze(cap, growth, new int[0], 0)).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(PaddockRotation.paddocks(5, 3)).isDeepEqualTo(PaddockRotation.paddocks(5, 3));
        assertThat(PaddockRotation.QUEST_ID).isEqualTo("q_green_pasture");
        assertThatThrownBy(() -> PaddockRotation.paddocks(1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PaddockRotation.best(new int[] {3}, new int[] {0}, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PaddockRotation.best(new int[] {3}, new int[] {1, 1}, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PaddockRotation.best(new int[] {3}, new int[] {1}, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    // Small paddock (cap 1, +1/day) and lush paddock (cap 4, +2/day) over four days: greedy
    // grazes the lush one again on day 3 for 2, the plan sacrifices day 3 and waits for a full 4.
    static final int[] CAP = {1, 4};
    static final int[] GROWTH = {1, 2};
    static final int DAYS = 4;

    private static int brute(int[] cap, int[] growth, int days) {
        int m = cap.length;
        int best = 0;
        int combos = (int) Math.pow(m, days);
        for (int c = 0; c < combos; c++) {
            int[] plan = new int[days];
            int x = c;
            for (int d = 0; d < days; d++) {
                plan[d] = x % m;
                x /= m;
            }
            best = Math.max(best, PaddockRotation.graze(cap, growth, plan, days));
        }
        return best;
    }
}
