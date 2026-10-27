// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.BilletWelds.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BilletWeldsTest {

    /** Brute force: try every weld at every step. */
    private static long brute(List<Long> row) {
        if (row.size() <= 1) {
            return 0;
        }
        long best = Long.MAX_VALUE;
        for (int i = 0; i + 1 < row.size(); i++) {
            List<Long> next = new ArrayList<>(row);
            long j = next.get(i) + next.get(i + 1);
            next.set(i, j);
            next.remove(i + 1);
            best = Math.min(best, j + brute(next));
        }
        return best;
    }

    private static long bruteChain(int[] d, int i, int j) {
        if (i == j) {
            return 0;
        }
        long best = Long.MAX_VALUE;
        for (int k = i; k < j; k++) {
            best = Math.min(best, bruteChain(d, i, k) + bruteChain(d, k + 1, j) + (long) d[i] * d[k + 1] * d[j + 1]);
        }
        return best;
    }

    private static List<Long> boxed(int[] w) {
        List<Long> l = new ArrayList<>();
        for (int x : w) {
            l.add((long) x);
        }
        return l;
    }

    @Test
    void leastHeatAndOrderMatchBruteForceOnSeededRows() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] w = BilletWelds.billets(seed, (int) (seed % 9), 1 + (int) (seed % 20));
            long least = BilletWelds.leastHeat(w);
            assertThat(least).as("seed %d", seed).isEqualTo(brute(boxed(w)));
            assertThat(BilletWelds.heat(w, BilletWelds.order(w))).isEqualTo(least);
        }
    }

    @Test
    void greedyNeverBeatsDpAndLoses() {
        int losses = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] w = BilletWelds.billets(seed * 17L, 8, 20);
            long g = BilletWelds.heat(w, BilletWelds.greedy(w));
            long b = BilletWelds.leastHeat(w);
            assertThat(g).isGreaterThanOrEqualTo(b);
            losses += g > b ? 1 : 0;
        }
        assertThat(losses).isPositive();
    }

    @Test
    void matrixChainMatchesBruteForceAndTextbook() {
        assertThat(BilletWelds.matrixChain(new int[] {10, 30, 5, 60})).isEqualTo(4500);
        assertThat(BilletWelds.matrixChain(new int[] {40, 20, 30, 10, 30})).isEqualTo(26000);
        for (long seed = 1; seed <= 100; seed++) {
            int[] d = BilletWelds.billets(seed, 2 + (int) (seed % 7), 30);
            assertThat(BilletWelds.matrixChain(d)).isEqualTo(bruteChain(d, 0, d.length - 2));
        }
    }

    @Test
    void handWorkedRowAndReplay() {
        int[] w = {4, 1, 1, 4};
        assertThat(BilletWelds.leastHeat(w)).isEqualTo(18);
        assertThat(BilletWelds.billets(216L, 7, 20)).isEqualTo(BilletWelds.billets(216L, 7, 20));
        assertThat(BilletWelds.order(BilletWelds.billets(216L, 7, 20)))
                .isEqualTo(BilletWelds.order(BilletWelds.billets(216L, 7, 20)));
        assertThat(BilletWelds.QUEST_ID).isEqualTo("q_billet_welds");
    }

    @Test
    void gradesLinesAndRejects() {
        assertThat(BilletWelds.grade(100, 100)).isEqualTo(Grade.SEAMLESS);
        assertThat(BilletWelds.grade(110, 100)).isEqualTo(Grade.WARM);
        assertThat(BilletWelds.grade(111, 100)).isEqualTo(Grade.SCORCHED);
        assertThatThrownBy(() -> BilletWelds.grade(99, 100)).isInstanceOf(IllegalArgumentException.class);
        assertThat(BilletWelds.forgemasterLine(200, 100)).contains("coal");
        assertThat(BilletWelds.leastHeat(new int[] {7})).isZero();
        assertThat(BilletWelds.order(new int[0])).isEmpty();
        assertThatThrownBy(() -> BilletWelds.heat(new int[] {1, 2}, List.of(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BilletWelds.heat(new int[] {1, 2}, List.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BilletWelds.billets(1L, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
