// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class GalleyStackTest {

    private static int[] shuffled(SplittableRandom rnd, int n) {
        int[] s = new int[n];
        for (int i = 0; i < n; i++) {
            s[i] = i;
        }
        for (int i = n - 1; i > 0; i--) {
            int j = rnd.nextInt(i + 1);
            int t = s[i];
            s[i] = s[j];
            s[j] = t;
        }
        return s;
    }

    private static boolean reach(int[] s, int d) {
        boolean ok = true;
        for (int i = 0; i < s.length && ok; i++) {
            ok = s[i] == i;
        }
        if (ok) {
            return true;
        }
        if (d == 0) {
            return false;
        }
        for (int k = 2; k <= s.length; k++) {
            if (reach(GalleyStack.flip(s, k), d - 1)) {
                return true;
            }
        }
        return false;
    }

    private static int[] replay(int[] s, int[] flips) {
        int[] cur = s;
        for (int k : flips) {
            cur = GalleyStack.flip(cur, k);
        }
        return cur;
    }

    @Test
    void exactMatchesIterativeDeepening() {
        SplittableRandom rnd = new SplittableRandom(428);
        for (int t = 0; t < 120; t++) {
            int[] s = shuffled(rnd, 1 + rnd.nextInt(6));
            int[] f = GalleyStack.fewest(s);
            assertThat(GalleyStack.sorted(replay(s, f))).isTrue();
            int d = 0;
            while (!reach(s, d)) {
                d++;
            }
            assertThat(f.length).isEqualTo(d);
        }
    }

    @Test
    void greedyReplaysWithinBound() {
        SplittableRandom rnd = new SplittableRandom(4280);
        for (int t = 0; t < 500; t++) {
            int n = 1 + rnd.nextInt(12);
            int[] s = shuffled(rnd, n);
            int[] g = GalleyStack.greedy(s);
            assertThat(GalleyStack.sorted(replay(s, g))).isTrue();
            assertThat(g.length).isLessThanOrEqualTo(Math.max(0, 2 * n - 3));
            if (n <= 7) {
                assertThat(g.length).isGreaterThanOrEqualTo(GalleyStack.fewest(s).length);
            }
        }
    }

    @Test
    void pancakeNumbers() {
        int[] want = {0, 1, 3, 4, 5, 7, 8};
        for (int n = 1; n <= 7; n++) {
            assertThat(GalleyStack.pancakeNumber(n)).as("n=%d", n).isEqualTo(want[n - 1]);
        }
    }

    @Test
    void questAndBounds() {
        assertThat(GalleyStack.quest(new int[] {1, 0, 2}, 1)).isTrue();
        assertThat(GalleyStack.quest(new int[] {0, 2, 1}, 3)).isTrue();
        assertThat(GalleyStack.quest(new int[] {0, 2, 1}, 2)).isFalse();
        assertThat(GalleyStack.fewest(new int[] {0, 1})).isEmpty();
        assertThat(GalleyStack.QUEST_ID).isEqualTo("q_galley_stack");
        assertThatThrownBy(() -> GalleyStack.flip(new int[] {0, 0}, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GalleyStack.flip(new int[] {0, 1}, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GalleyStack.fewest(new int[9])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GalleyStack.pancakeNumber(9)).isInstanceOf(IllegalArgumentException.class);
    }
}