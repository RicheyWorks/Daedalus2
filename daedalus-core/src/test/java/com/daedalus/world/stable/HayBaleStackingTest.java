// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.HayBaleStacking.Bales;
import com.daedalus.world.stable.HayBaleStacking.Stack;

import java.util.Arrays;
import org.junit.jupiter.api.Test;

class HayBaleStackingTest {

    @Test
    void bestMatchesBruteForceOverEverySubset() {
        for (long seed = 1; seed <= 300; seed++) {
            Bales bales = HayBaleStacking.bales(seed, (int) (seed % 11));
            Stack s = HayBaleStacking.best(bales);
            assertThat(s.height()).as("seed %d", seed).isEqualTo(brute(bales));
            assertThat(HayBaleStacking.stack(bales, s.bottomUp())).isEqualTo(s.height());
            assertThat(HayBaleStacking.quest(bales, s.bottomUp())).isTrue();
        }
    }

    @Test
    void biggestFirstIsNeverTallerAndUsuallyShorter() {
        // Ten bales: the habit came out shorter on 268 of these 300 seeds when this was written.
        int shorter = 0;
        for (long seed = 1; seed <= 300; seed++) {
            Bales bales = HayBaleStacking.bales(seed, 10);
            Stack g = HayBaleStacking.biggestFirst(bales);
            Stack b = HayBaleStacking.best(bales);
            assertThat(HayBaleStacking.stack(bales, g.bottomUp())).isEqualTo(g.height());
            assertThat(g.height()).isLessThanOrEqualTo(b.height());
            if (g.height() < b.height()) {
                shorter++;
            }
        }
        assertThat(shorter).isGreaterThan(200);
    }

    @Test
    void weakBigBaleCrushesTheHabit() {
        // Bale 0 is the biggest but carries nothing (strength 0); bale 1 is small, tall and strong.
        // Biggest-first lays bale 0 and can add nothing: height 1. Best stands bale 1 alone: 9.
        Bales bales = new Bales(new int[] {10, 5}, new int[] {10, 5}, new int[] {1, 9}, new int[] {5, 1},
                new int[] {0, 9});
        assertThat(HayBaleStacking.biggestFirst(bales)).isEqualTo(new Stack(1, new int[] {0}));
        assertThat(HayBaleStacking.best(bales)).isEqualTo(new Stack(9, new int[] {1}));
        assertThat(HayBaleStacking.quest(bales, new int[] {0})).isFalse();
        // Turning: a 3x7 bale fits on a 8x4 bale (3 < 4, 7 < 8).
        Bales turned = new Bales(new int[] {8, 3}, new int[] {4, 7}, new int[] {2, 3}, new int[] {1, 1},
                new int[] {1, 0});
        assertThat(HayBaleStacking.best(turned).height()).isEqualTo(5);
    }

    @Test
    void badStacksAreInvalid() {
        Bales bales = new Bales(new int[] {6, 4, 2}, new int[] {6, 4, 2}, new int[] {1, 1, 1}, new int[] {2, 2, 2},
                new int[] {3, 2, 0});
        assertThat(HayBaleStacking.stack(bales, new int[] {0, 1})).isEqualTo(2);
        assertThat(HayBaleStacking.stack(bales, new int[] {0, 1, 2})).isEqualTo(HayBaleStacking.INVALID);
        assertThat(HayBaleStacking.stack(bales, new int[] {1, 0})).isEqualTo(HayBaleStacking.INVALID);
        assertThat(HayBaleStacking.stack(bales, new int[] {0, 0})).isEqualTo(HayBaleStacking.INVALID);
        assertThat(HayBaleStacking.stack(bales, new int[] {3})).isEqualTo(HayBaleStacking.INVALID);
        assertThat(HayBaleStacking.stack(bales, new int[0])).isZero();
        assertThat(HayBaleStacking.best(HayBaleStacking.bales(1, 0)).height()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(HayBaleStacking.bales(6, 9)).isEqualTo(HayBaleStacking.bales(6, 9));
        assertThat(HayBaleStacking.QUEST_ID).isEqualTo("q_tall_stack");
        assertThatThrownBy(() -> HayBaleStacking.bales(1, 17)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Bales(new int[] {1}, new int[] {1}, new int[] {1}, new int[] {10}, new int[] {1}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Bales(new int[] {0}, new int[] {1}, new int[] {1}, new int[] {1}, new int[] {1}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    /** Every subset, laid in footprint order (the only order a legal stack can have). */
    private static int brute(Bales bales) {
        int n = bales.size();
        int[] a = bales.a();
        int[] b = bales.b();
        int best = 0;
        for (int mask = 0; mask < (1 << n); mask++) {
            Integer[] ids = new Integer[Integer.bitCount(mask)];
            int k = 0;
            for (int i = 0; i < n; i++) {
                if ((mask & (1 << i)) != 0) {
                    ids[k++] = i;
                }
            }
            Arrays.sort(ids, (x, y) -> Integer.compare(a[y] * b[y], a[x] * b[x]));
            int[] order = new int[ids.length];
            for (int i = 0; i < ids.length; i++) {
                order[i] = ids[i];
            }
            best = Math.max(best, HayBaleStacking.stack(bales, order));
        }
        return best;
    }
}
