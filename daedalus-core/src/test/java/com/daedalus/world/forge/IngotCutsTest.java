// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.IngotCuts.Cut;
import com.daedalus.world.forge.IngotCuts.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IngotCutsTest {

    /** Brute force over every composition of n (2^(n-1) cut patterns). */
    private static int bruteForce(int[] p, int n, int kerf) {
        if (n == 0) {
            return 0;
        }
        int best = Integer.MIN_VALUE;
        for (int mask = 0; mask < (1 << (n - 1)); mask++) {
            List<Integer> pieces = new ArrayList<>();
            int run = 1;
            for (int i = 0; i < n - 1; i++) {
                if ((mask >> i & 1) == 1) {
                    pieces.add(run);
                    run = 1;
                } else {
                    run++;
                }
            }
            pieces.add(run);
            best = Math.max(best, IngotCuts.value(p, kerf, pieces));
        }
        return best;
    }

    @Test
    void exactCutMatchesBruteForceOnSeededQuays() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = 1 + (int) (seed % 14);
            int kerf = (int) (seed % 4);
            int[] p = IngotCuts.quayPrices(seed, n);
            Cut c = IngotCuts.best(p, n, kerf);
            assertThat(c.value()).as("seed %d", seed).isEqualTo(bruteForce(p, n, kerf));
            assertThat(IngotCuts.value(p, kerf, c.pieces())).isEqualTo(c.value());
            assertThat(c.pieces().stream().mapToInt(Integer::intValue).sum()).isEqualTo(n);
        }
    }

    @Test
    void greedyNeverBeatsBestAndLosesOnTheClassicPriceList() {
        int[] p = {0, 1, 5, 8, 9};
        assertThat(IngotCuts.greedy(p, 4, 0).pieces()).containsExactly(3, 1);
        assertThat(IngotCuts.greedy(p, 4, 0).value()).isEqualTo(9);
        assertThat(IngotCuts.best(p, 4, 0).value()).isEqualTo(10);
        int losses = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] q = IngotCuts.quayPrices(seed, 12);
            int b = IngotCuts.best(q, 12, 1).value();
            int g = IngotCuts.greedy(q, 12, 1).value();
            assertThat(g).isLessThanOrEqualTo(b);
            if (g < b) {
                losses++;
            }
        }
        assertThat(losses).isPositive();
    }

    @Test
    void kerfFeeDiscouragesCutting() {
        int[] p = {0, 3, 6, 9, 12};
        assertThat(IngotCuts.best(p, 4, 0).value()).isEqualTo(12);
        assertThat(IngotCuts.best(p, 4, 1).pieces()).containsExactly(4);
        assertThat(IngotCuts.value(p, 2, List.of(1, 1, 2))).isEqualTo(3 + 3 + 6 - 4);
    }

    @Test
    void sameSeedReplaysAndBarComesFromTheFiring() {
        assertThat(IngotCuts.quayPrices(190L, 12)).isEqualTo(IngotCuts.quayPrices(190L, 12));
        assertThat(IngotCuts.quayPrices(191L, 12)).isNotEqualTo(IngotCuts.quayPrices(190L, 12));
        CrucibleLoads.Firing f = CrucibleLoads.fire(CrucibleLoads.haul(189L, 14, 30),
                CrucibleLoads.Rule.FIRST_FIT_DECREASING);
        int bar = IngotCuts.barFrom(f);
        assertThat(bar).isEqualTo(Math.min(IngotCuts.MAX_BAR, f.used() * IngotCuts.UNITS_PER_CRUCIBLE));
        int[] p = IngotCuts.quayPrices(190L, IngotCuts.MAX_BAR);
        assertThat(IngotCuts.best(p, bar, 1)).isEqualTo(IngotCuts.best(p, bar, 1));
    }

    @Test
    void gradesAndLines() {
        assertThat(IngotCuts.grade(100, 100)).isEqualTo(Grade.MASTERWORK);
        assertThat(IngotCuts.grade(90, 100)).isEqualTo(Grade.FAIR);
        assertThat(IngotCuts.grade(89, 100)).isEqualTo(Grade.SCRAP);
        assertThatThrownBy(() -> IngotCuts.grade(101, 100)).isInstanceOf(IllegalArgumentException.class);
        int[] p = {0, 1, 5, 8, 9};
        Cut g = IngotCuts.greedy(p, 4, 0);
        assertThat(IngotCuts.forgemasterLine(g, 10)).contains("9 of 10");
        assertThat(IngotCuts.QUEST_ID).isEqualTo("q_ingot_cuts");
    }

    @Test
    void edgeCasesAndRejects() {
        int[] p = {0, 2, 4};
        assertThat(IngotCuts.best(p, 0, 1).pieces()).isEmpty();
        assertThat(IngotCuts.greedy(p, 0, 1).value()).isZero();
        assertThatThrownBy(() -> IngotCuts.best(p, 3, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotCuts.best(p, 2, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotCuts.quayPrices(1L, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IngotCuts.value(p, 0, List.of(3))).isInstanceOf(IllegalArgumentException.class);
    }
}
