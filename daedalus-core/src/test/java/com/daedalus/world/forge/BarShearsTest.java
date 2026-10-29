// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.BarShears.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BarShearsTest {

    private static long brute(long[] price, int left, long toll, boolean firstPiece) {
        if (left == 0) {
            return 0;
        }
        long best = Long.MIN_VALUE;
        for (int k = 1; k <= left; k++) {
            best = Math.max(best, price[k - 1] + brute(price, left - k, toll, false));
        }
        return best - (firstPiece ? 0 : toll);
    }

    @Test
    void matchesBruteForceOnSeededPriceLists() {
        for (long seed = 0; seed < 250; seed++) {
            int n = 1 + (int) (seed % 12);
            long[] p = BarShears.prices(seed, n, 1 + (int) (seed % 30));
            long toll = seed % 5;
            for (int len = 1; len <= n; len++) {
                long want = brute(p, len, toll, true);
                assertThat(BarShears.bestTake(p, len, toll)).as("seed %d len %d", seed, len).isEqualTo(want);
                int[] cut = BarShears.pieces(p, len, toll);
                assertThat(BarShears.take(p, cut, toll)).isEqualTo(want);
                assertThat(BarShears.grade(p, len, toll, cut)).isEqualTo(Grade.PROFIT);
            }
        }
    }

    @Test
    void knownPriceLists() {
        long[] clrs = {1, 5, 8, 9, 10, 17, 17, 20};
        assertThat(BarShears.bestTake(clrs, 8, 0)).isEqualTo(22);
        assertThat(BarShears.pieces(clrs, 8, 0)).containsExactly(2, 6);
        assertThat(BarShears.bestTake(clrs, 4, 0)).isEqualTo(10);
        assertThat(BarShears.bestTake(clrs, 4, 2)).isEqualTo(9);
        assertThat(BarShears.pieces(clrs, 4, 2)).containsExactly(4);
        assertThatThrownBy(() -> BarShears.bestTake(clrs, 9, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BarShears.bestTake(clrs, 3, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        long[] clrs = {1, 5, 8, 9, 10, 17, 17, 20};
        assertThat(BarShears.grade(clrs, 8, 0, new int[] {6, 2})).isEqualTo(Grade.PROFIT);
        assertThat(BarShears.grade(clrs, 8, 0, new int[] {8})).isEqualTo(Grade.SHORTED);
        assertThat(BarShears.grade(clrs, 8, 0, new int[] {6, 1})).isEqualTo(Grade.SHORTED);
        assertThat(BarShears.grade(clrs, 8, 0, new int[] {0, 8})).isEqualTo(Grade.SHORTED);
        for (Grade g : Grade.values()) {
            assertThat(BarShears.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(BarShears.QUEST_ID).isEqualTo("q_bar_shears");
        assertThat(BarShears.prices(3, 6, 9)).containsExactly(BarShears.prices(3, 6, 9));
        assertThatThrownBy(() -> BarShears.prices(1, 0, 9)).isInstanceOf(IllegalArgumentException.class);
    }
}
