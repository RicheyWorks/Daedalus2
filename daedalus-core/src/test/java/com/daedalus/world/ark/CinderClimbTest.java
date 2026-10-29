// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.CinderClimb.Climb;

import org.junit.jupiter.api.Test;

class CinderClimbTest {

    @Test
    void longestMatchesBruteForceAndPathIsValid() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] h = CinderClimb.shelf(seed, (int) (seed % 15), 12);
            Climb c = CinderClimb.longest(h);
            assertThat(c.length()).as("seed %d", seed).isEqualTo(brute(h));
            assertThat(c.ledges()).hasSize(c.length());
            assertThat(CinderClimb.valid(h, c.ledges())).isTrue();
        }
    }

    @Test
    void greedyIsValidNeverLongerAndSometimesShorter() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            int[] h = CinderClimb.shelf(seed, 30, 50);
            Climb g = CinderClimb.greedy(h);
            int best = CinderClimb.longest(h).length();
            assertThat(CinderClimb.valid(h, g.ledges())).isTrue();
            assertThat(g.length()).isLessThanOrEqualTo(best);
            lost |= g.length() < best;
        }
        assertThat(lost).isTrue();
    }

    @Test
    void tallEarlyLedgeStrandsTheGreedyScouts() {
        int[] h = {9, 1, 2, 3, 4, 10};
        assertThat(CinderClimb.greedy(h).length()).isEqualTo(2);
        Climb best = CinderClimb.longest(h);
        assertThat(best.length()).isEqualTo(5);
        assertThat(best.ledges()).containsExactly(1, 2, 3, 4, 5);
    }

    @Test
    void equalHeightsAreNotAStepAndEdgeCases() {
        assertThat(CinderClimb.longest(new int[] {5, 5, 5}).length()).isEqualTo(1);
        assertThat(CinderClimb.longest(new int[0]).length()).isZero();
        assertThat(CinderClimb.valid(new int[] {1, 1}, new int[] {0, 1})).isFalse();
        assertThat(CinderClimb.shelf(4, 20, 9)).isEqualTo(CinderClimb.shelf(4, 20, 9));
        assertThatThrownBy(() -> CinderClimb.shelf(1, -1, 5)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questNeedsTheLongestValidClimb() {
        int[] h = {9, 1, 2, 3, 4, 10};
        assertThat(CinderClimb.quest(h, new int[] {1, 2, 3, 4, 5})).isTrue();
        assertThat(CinderClimb.quest(h, new int[] {0, 5})).isFalse();
        assertThat(CinderClimb.quest(h, new int[] {5, 4, 3, 2, 1})).isFalse();
        assertThat(CinderClimb.QUEST_ID).isEqualTo("q_cinder_climb");
    }

    private static int brute(int[] h) {
        int best = 0;
        for (int mask = 0; mask < (1 << h.length); mask++) {
            int last = Integer.MIN_VALUE;
            int len = 0;
            boolean ok = true;
            for (int i = 0; i < h.length && ok; i++) {
                if ((mask & (1 << i)) != 0) {
                    ok = h[i] > last;
                    last = h[i];
                    len++;
                }
            }
            if (ok) {
                best = Math.max(best, len);
            }
        }
        return best;
    }
}
