// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.ShoeingShed.Queue;

import org.junit.jupiter.api.Test;

class ShoeingShedTest {

    @Test
    void bestMatchesBruteForceAndOrderCostsWhatItClaims() {
        for (long seed = 1; seed <= 300; seed++) {
            int[][] h = ShoeingShed.horses(seed, (int) (seed % 8));
            Queue q = ShoeingShed.best(h[0], h[1], h[2]);
            assertThat(q.penalty()).as("seed %d", seed).isEqualTo(brute(h[0], h[1], h[2]));
            assertThat(ShoeingShed.penalty(h[0], h[1], h[2], q.order())).isEqualTo(q.penalty());
            assertThat(ShoeingShed.quest(h[0], h[1], h[2], q.order())).isTrue();
        }
    }

    @Test
    void smithIsLegalNeverBetterAndSometimesWorse() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            int[][] h = ShoeingShed.horses(seed, 10);
            Queue s = ShoeingShed.smith(h[0], h[1], h[2]);
            Queue b = ShoeingShed.best(h[0], h[1], h[2]);
            assertThat(ShoeingShed.penalty(h[0], h[1], h[2], s.order())).isEqualTo(s.penalty());
            assertThat(s.penalty()).isGreaterThanOrEqualTo(b.penalty());
            lost |= s.penalty() > b.penalty();
        }
        assertThat(lost).isTrue();
    }

    @Test
    void earlyCalledHorseGoesFirstEvenThoughItFretsLess() {
        int[] time = {2, 4};
        int[] fret = {1, 3};
        int[] due = {2, 10};
        Queue s = ShoeingShed.smith(time, fret, due);
        Queue b = ShoeingShed.best(time, fret, due);
        assertThat(s.order()).containsExactly(1, 0);
        assertThat(s.penalty()).isEqualTo(4);
        assertThat(b.order()).containsExactly(0, 1);
        assertThat(b.penalty()).isZero();
        assertThat(ShoeingShed.quest(time, fret, due, s.order())).isFalse();
    }

    @Test
    void illegalOrdersScoreMinusOne() {
        int[] time = {1, 2};
        int[] fret = {1, 1};
        int[] due = {0, 0};
        assertThat(ShoeingShed.penalty(time, fret, due, new int[] {0, 0})).isEqualTo(-1);
        assertThat(ShoeingShed.penalty(time, fret, due, new int[] {0})).isEqualTo(-1);
        assertThat(ShoeingShed.penalty(time, fret, due, new int[] {0, 2})).isEqualTo(-1);
        assertThat(ShoeingShed.penalty(time, fret, due, new int[] {0, 1})).isEqualTo(1 + 3);
        assertThat(ShoeingShed.best(new int[0], new int[0], new int[0]).penalty()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(ShoeingShed.horses(3, 6)).isDeepEqualTo(ShoeingShed.horses(3, 6));
        assertThat(ShoeingShed.QUEST_ID).isEqualTo("q_sound_hooves");
        assertThatThrownBy(() -> ShoeingShed.horses(1, 17)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ShoeingShed.best(new int[] {0}, new int[] {1}, new int[] {1})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ShoeingShed.best(new int[] {1}, new int[] {1}, new int[0])).isInstanceOf(IllegalArgumentException.class);
    }

    private static long brute(int[] time, int[] fret, int[] due) {
        int n = time.length;
        int[] perm = new int[n];
        for (int i = 0; i < n; i++) {
            perm[i] = i;
        }
        long[] best = {Long.MAX_VALUE};
        permute(perm, 0, time, fret, due, best);
        return n == 0 ? 0 : best[0];
    }

    private static void permute(int[] p, int k, int[] time, int[] fret, int[] due, long[] best) {
        if (k == p.length) {
            best[0] = Math.min(best[0], ShoeingShed.penalty(time, fret, due, p));
            return;
        }
        for (int i = k; i < p.length; i++) {
            int t = p[k];
            p[k] = p[i];
            p[i] = t;
            permute(p, k + 1, time, fret, due, best);
            p[i] = p[k];
            p[k] = t;
        }
    }
}
