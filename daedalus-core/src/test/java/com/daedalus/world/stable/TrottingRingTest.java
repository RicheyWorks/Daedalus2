// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.TrottingRing.Round;

import org.junit.jupiter.api.Test;

class TrottingRingTest {

    @Test
    void bestMatchesBruteForceAndPlanScoresWhatItClaims() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 9);
            int stamina = (int) (seed % 4);
            int[] calls = TrottingRing.calls(seed, n);
            Round r = TrottingRing.best(calls, stamina);
            assertThat(r.score()).as("seed %d", seed).isEqualTo(brute(calls, stamina));
            assertThat(r.gaits()).hasSize(n);
            assertThat(TrottingRing.score(calls, r.gaits(), stamina)).isEqualTo(r.score());
            assertThat(TrottingRing.quest(calls, r.gaits(), stamina)).isTrue();
        }
    }

    @Test
    void eagerIsLegalNeverBetterAndSometimesWorse() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            int[] calls = TrottingRing.calls(seed, 20);
            Round e = TrottingRing.eager(calls, 3);
            Round b = TrottingRing.best(calls, 3);
            assertThat(TrottingRing.score(calls, e.gaits(), 3)).isEqualTo(e.score());
            assertThat(e.score()).isLessThanOrEqualTo(b.score());
            lost |= e.score() < b.score();
        }
        assertThat(lost).isTrue();
    }

    @Test
    void savingStaminaForTheFinalCanterBeatsObeyingEveryCall() {
        int[] calls = {TrottingRing.TROT, TrottingRing.TROT, TrottingRing.CANTER};
        Round eager = TrottingRing.eager(calls, 2);
        Round best = TrottingRing.best(calls, 2);
        assertThat(eager.gaits()).containsExactly(TrottingRing.TROT, TrottingRing.TROT, TrottingRing.WALK);
        assertThat(eager.score()).isEqualTo(4);
        assertThat(best.gaits()).containsExactly(TrottingRing.TROT, TrottingRing.WALK, TrottingRing.CANTER);
        assertThat(best.score()).isEqualTo(5);
        assertThat(TrottingRing.quest(calls, eager.gaits(), 2)).isFalse();
        assertThat(TrottingRing.quest(calls, best.gaits(), 2)).isTrue();
    }

    @Test
    void illegalPlansScoreMinusOne() {
        int[] calls = {TrottingRing.CANTER, TrottingRing.CANTER};
        assertThat(TrottingRing.score(calls, new int[] {TrottingRing.CANTER, TrottingRing.CANTER}, 3)).isEqualTo(-1);
        assertThat(TrottingRing.score(calls, new int[] {TrottingRing.CANTER}, 3)).isEqualTo(-1);
        assertThat(TrottingRing.score(calls, new int[] {3, 0}, 3)).isEqualTo(-1);
        assertThat(TrottingRing.quest(calls, new int[] {TrottingRing.CANTER}, 3)).isFalse();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(TrottingRing.calls(42, 12)).containsExactly(TrottingRing.calls(42, 12));
        assertThat(TrottingRing.best(new int[0], 0).score()).isZero();
        assertThat(TrottingRing.points(TrottingRing.WALK, TrottingRing.CANTER)).isZero();
        assertThat(TrottingRing.cost(TrottingRing.WALK)).isEqualTo(-1);
        assertThat(TrottingRing.QUEST_ID).isEqualTo("q_blue_rosette");
        assertThatThrownBy(() -> TrottingRing.calls(1, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrottingRing.best(new int[] {1}, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrottingRing.points(5, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(int[] calls, int stamina) {
        int n = calls.length;
        int best = 0;
        int combos = (int) Math.pow(3, n);
        boolean any = false;
        for (int m = 0; m < combos; m++) {
            int[] g = new int[n];
            int x = m;
            for (int i = 0; i < n; i++) {
                g[i] = x % 3;
                x /= 3;
            }
            int s = TrottingRing.score(calls, g, stamina);
            if (s >= 0 && (!any || s > best)) {
                best = s;
                any = true;
            }
        }
        return best;
    }
}
