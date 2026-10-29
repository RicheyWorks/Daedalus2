// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.StallPlaques.Layout;

import org.junit.jupiter.api.Test;

class StallPlaquesTest {

    @Test
    void bestMatchesBruteForceOverEveryBreakSet() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 13);
            int[] len = StallPlaques.names(seed, n, 1, 7);
            int width = 7 + (int) (seed % 6);
            Layout b = StallPlaques.best(len, width);
            assertThat(b.ugliness()).as("seed %d", seed).isEqualTo(brute(len, width));
            assertThat(StallPlaques.ugliness(len, width, b.breaks())).isEqualTo(b.ugliness());
            assertThat(StallPlaques.quest(len, width, b.breaks())).isTrue();
        }
    }

    @Test
    void fillEachLineIsNeverNeaterAndOftenUglier() {
        // 25 names of 2-9 letters on 15-wide plaques: the habit was uglier on 184 of these 300 seeds when written.
        int uglier = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] len = StallPlaques.names(seed, 25, 2, 9);
            Layout g = StallPlaques.fillEachLine(len, 15);
            Layout b = StallPlaques.best(len, 15);
            assertThat(StallPlaques.ugliness(len, 15, g.breaks())).isEqualTo(g.ugliness());
            assertThat(g.ugliness()).isGreaterThanOrEqualTo(b.ugliness());
            if (g.ugliness() > b.ugliness()) {
                uglier++;
            }
        }
        assertThat(uglier).isGreaterThan(150);
    }

    @Test
    void fullFirstLineLeavesAStub() {
        // Names of 3, 2, 2 and 5 letters on 6-wide plaques. Filling: "aaa bb" (0), "cc" (4 left, 16), last line: 16.
        // Breaking early: "aaa" (3 left, 9), "bb cc" (1 left, 1), last line: 10.
        int[] len = {3, 2, 2, 5};
        assertThat(StallPlaques.fillEachLine(len, 6)).isEqualTo(new Layout(16, new int[] {2, 3}));
        assertThat(StallPlaques.best(len, 6)).isEqualTo(new Layout(10, new int[] {1, 3}));
        assertThat(StallPlaques.quest(len, 6, new int[] {2, 3})).isFalse();
    }

    @Test
    void badLayoutsAreInvalid() {
        int[] len = {3, 2, 2, 5};
        assertThat(StallPlaques.ugliness(len, 6, new int[] {1, 2, 3})).isEqualTo(9 + 16 + 16);
        assertThat(StallPlaques.ugliness(len, 6, new int[] {3})).isEqualTo(StallPlaques.INVALID);
        assertThat(StallPlaques.ugliness(len, 6, new int[] {2, 2})).isEqualTo(StallPlaques.INVALID);
        assertThat(StallPlaques.ugliness(len, 6, new int[] {3, 1})).isEqualTo(StallPlaques.INVALID);
        assertThat(StallPlaques.ugliness(len, 6, new int[] {1, 3, 4})).isEqualTo(StallPlaques.INVALID);
        assertThat(StallPlaques.ugliness(len, 6, new int[] {0, 1, 3})).isEqualTo(StallPlaques.INVALID);
        assertThat(StallPlaques.best(new int[0], 5).ugliness()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(StallPlaques.names(3, 9, 2, 6)).containsExactly(StallPlaques.names(3, 9, 2, 6));
        assertThat(StallPlaques.QUEST_ID).isEqualTo("q_neat_plaques");
        assertThatThrownBy(() -> StallPlaques.names(1, 3, 0, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StallPlaques.best(new int[] {7}, 6)).isInstanceOf(IllegalArgumentException.class);
    }

    private static long brute(int[] len, int width) {
        int n = len.length;
        if (n == 0) {
            return 0;
        }
        long best = Long.MAX_VALUE;
        for (int mask = 0; mask < (1 << (n - 1)); mask++) {
            int[] breaks = new int[Integer.bitCount(mask)];
            int k = 0;
            for (int i = 1; i < n; i++) {
                if ((mask & (1 << (i - 1))) != 0) {
                    breaks[k++] = i;
                }
            }
            long u = StallPlaques.ugliness(len, width, breaks);
            if (u != StallPlaques.INVALID) {
                best = Math.min(best, u);
            }
        }
        return best;
    }
}
