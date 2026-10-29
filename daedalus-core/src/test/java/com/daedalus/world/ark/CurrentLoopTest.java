// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CurrentLoopTest {

    private static CurrentLoop.Drift naive(int[] f, int start) {
        int[] seen = new int[f.length];
        Arrays.fill(seen, -1);
        int x = start;
        int t = 0;
        while (seen[x] < 0) {
            seen[x] = t++;
            x = f[x];
        }
        return new CurrentLoop.Drift(seen[x], t - seen[x]);
    }

    @Test
    void floydAndBrentMatchVisitedWalk() {
        SplittableRandom rnd = new SplittableRandom(290);
        for (int trial = 0; trial < 2000; trial++) {
            int m = rnd.nextInt(1, 400);
            int[] f = CurrentLoop.currents(m, rnd.nextLong());
            int start = rnd.nextInt(m);
            CurrentLoop.Drift want = naive(f, start);
            assertThat(CurrentLoop.floyd(i -> f[i], start)).isEqualTo(want);
            assertThat(CurrentLoop.brent(i -> f[i], start)).isEqualTo(want);
            assertThat(CurrentLoop.drift(f, start)).isEqualTo(want);
        }
    }

    @Test
    void handBuiltCurrents() {
        int[] rho = {1, 2, 3, 4, 5, 3};
        assertThat(CurrentLoop.drift(rho, 0)).isEqualTo(new CurrentLoop.Drift(3, 3));
        assertThat(CurrentLoop.drift(new int[] {0}, 0)).isEqualTo(new CurrentLoop.Drift(0, 1));
        int big = 1_000_000;
        assertThat(CurrentLoop.brent(i -> (i + 1) % big, 0)).isEqualTo(new CurrentLoop.Drift(0, big));
        assertThat(CurrentLoop.floyd(i -> i < 5000 ? i + 1 : 4000 + (i - 4000 + 1) % 1001, 0))
                .isEqualTo(new CurrentLoop.Drift(4000, 1001));
    }

    @Test
    void questAndBounds() {
        int[] rho = {1, 2, 3, 4, 5, 3};
        assertThat(CurrentLoop.quest(rho, 0, 3, 3)).isTrue();
        assertThat(CurrentLoop.quest(rho, 4, 0, 3)).isTrue();
        assertThat(CurrentLoop.quest(rho, 0, 2, 3)).isFalse();
        assertThat(CurrentLoop.QUEST_ID).isEqualTo("q_current_loop");
        assertThatThrownBy(() -> CurrentLoop.drift(rho, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CurrentLoop.drift(new int[] {1}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CurrentLoop.currents(0, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}