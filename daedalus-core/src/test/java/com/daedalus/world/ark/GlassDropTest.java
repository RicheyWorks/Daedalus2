// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.GlassDrop.Run;

import org.junit.jupiter.api.Test;

class GlassDropTest {

    @Test
    void minDropsMatchesMinimaxBruteForce() {
        int[][] memo = new int[5][61];
        for (int k = 1; k <= 4; k++) {
            for (int n = 0; n <= 60; n++) {
                assertThat(GlassDrop.minDrops(k, n)).as("k=%d n=%d", k, n)
                        .isEqualTo(brute(k, n, memo));
            }
        }
    }

    @Test
    void strategyAlwaysFindsTheRungWithinTheBound() {
        for (int k = 1; k <= 4; k++) {
            for (int n = 0; n <= 60; n++) {
                int bound = GlassDrop.minDrops(k, n);
                int worst = 0;
                for (int safe = 0; safe <= n; safe++) {
                    Run r = GlassDrop.simulate(k, n, safe);
                    assertThat(r.safeRung()).isEqualTo(safe);
                    assertThat(r.bottlesBroken()).isLessThanOrEqualTo(k);
                    worst = Math.max(worst, r.drops());
                }
                assertThat(worst).as("k=%d n=%d", k, n).isEqualTo(bound);
            }
        }
    }

    @Test
    void classicValuesAndLinearIsWorse() {
        assertThat(GlassDrop.minDrops(2, 100)).isEqualTo(14);
        assertThat(GlassDrop.minDrops(1, 100)).isEqualTo(100);
        assertThat(GlassDrop.minDrops(3, 100)).isEqualTo(9);
        assertThat(GlassDrop.nextRung(2, 100)).isEqualTo(14);
        assertThat(GlassDrop.coverable(2, 14)).isEqualTo(105);
        assertThat(GlassDrop.coverable(40, 200)).isPositive();
    }

    @Test
    void questAndValidation() {
        assertThat(GlassDrop.quest(2, 100, 14)).isTrue();
        assertThat(GlassDrop.quest(2, 100, 13)).isFalse();
        assertThat(GlassDrop.minDrops(0, 0)).isZero();
        assertThat(GlassDrop.QUEST_ID).isEqualTo("q_glass_drop");
        assertThatThrownBy(() -> GlassDrop.minDrops(0, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GlassDrop.simulate(2, 5, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GlassDrop.coverable(-1, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(int k, int n, int[][] memo) {
        if (n == 0) {
            return 0;
        }
        if (k == 1) {
            return n;
        }
        if (memo[k][n] != 0) {
            return memo[k][n];
        }
        int best = Integer.MAX_VALUE;
        for (int x = 1; x <= n; x++) {
            best = Math.min(best, 1 + Math.max(brute(k - 1, x - 1, memo), brute(k, n - x, memo)));
        }
        memo[k][n] = best;
        return best;
    }
}
