// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.TemperTrials.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TemperTrialsTest {

    @Test
    void minTrialsMatchMinimaxDp() {
        int maxK = 4;
        int maxN = 60;
        int[][] dp = new int[maxK + 1][maxN + 1];
        for (int k = 1; k <= maxK; k++) {
            for (int n = 1; n <= maxN; n++) {
                int best = k == 1 ? n : Integer.MAX_VALUE;
                for (int x = 1; k > 1 && x <= n; x++) {
                    best = Math.min(best, 1 + Math.max(dp[k - 1][x - 1], dp[k][n - x]));
                }
                dp[k][n] = best;
                assertThat(TemperTrials.minTrials(k, n)).as("k %d n %d", k, n).isEqualTo(best);
            }
        }
        assertThat(TemperTrials.minTrials(2, 100)).isEqualTo(14);
        assertThat(TemperTrials.minTrials(1, 0)).isZero();
    }

    @Test
    void strategyPinsEveryCrackPointWithinTheBound() {
        for (int k = 1; k <= 4; k++) {
            for (int n = 0; n <= 40; n++) {
                int bound = TemperTrials.minTrials(k, n);
                int worst = 0;
                for (int c = 0; c <= n; c++) {
                    worst = Math.max(worst, TemperTrials.play(k, n, c));
                }
                assertThat(worst).as("k %d n %d", k, n).isEqualTo(bound);
            }
        }
        for (long seed = 0; seed < 100; seed++) {
            int n = 1000 + (int) seed;
            int c = TemperTrials.crackPoint(seed, n);
            assertThat(TemperTrials.play(3, n, c)).isLessThanOrEqualTo(TemperTrials.minTrials(3, n));
        }
    }

    @Test
    void edgesGradesLinesAndReplay() {
        assertThat(TemperTrials.cover(200, 64)).isEqualTo(Long.MAX_VALUE);
        assertThat(TemperTrials.cover(3, 2)).isEqualTo(6);
        assertThatThrownBy(() -> TemperTrials.minTrials(0, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TemperTrials.nextProbe(2, 3, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TemperTrials.play(2, 5, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThat(TemperTrials.grade(2, 100, 14)).isEqualTo(Grade.MASTERFUL);
        assertThat(TemperTrials.grade(2, 100, 15)).isEqualTo(Grade.WASTEFUL);
        for (Grade g : Grade.values()) {
            assertThat(TemperTrials.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TemperTrials.QUEST_ID).isEqualTo("q_temper_trials");
        assertThat(TemperTrials.crackPoint(9, 50)).isEqualTo(TemperTrials.crackPoint(9, 50)).isBetween(0, 50);
    }
}
