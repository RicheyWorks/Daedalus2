// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.FeedLoft.Bale;
import com.daedalus.world.stable.FeedLoft.Load;

import java.util.List;

import org.junit.jupiter.api.Test;

class FeedLoftTest {

    @Test
    void bestMatchesBruteForceAndLoadIsLegal() {
        for (long seed = 1; seed <= 300; seed++) {
            List<Bale> bales = FeedLoft.delivery(seed, (int) (seed % 11), 6);
            int maxW = (int) (seed % 13);
            int maxB = (int) ((seed * 7) % 13);
            Load best = FeedLoft.best(bales, maxW, maxB);
            assertThat(best.nourishment()).as("seed %d", seed).isEqualTo(brute(bales, maxW, maxB));
            assertThat(FeedLoft.stack(bales, best.bales(), maxW, maxB)).isEqualTo(best.nourishment());
            assertThat(FeedLoft.quest(bales, best.bales(), maxW, maxB)).isTrue();
        }
    }

    @Test
    void greedyIsLegalNeverBetterAndSometimesWorse() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            List<Bale> bales = FeedLoft.delivery(seed, 14, 8);
            Load g = FeedLoft.greedy(bales, 20, 20);
            Load b = FeedLoft.best(bales, 20, 20);
            assertThat(FeedLoft.stack(bales, g.bales(), 20, 20)).isEqualTo(g.nourishment());
            assertThat(g.nourishment()).isLessThanOrEqualTo(b.nourishment());
            lost |= g.nourishment() < b.nourishment();
        }
        assertThat(lost).isTrue();
    }

    @Test
    void lightBulkyBalesFillTheLoftBeforeTheDenseOne() {
        List<Bale> bales = List.of(new Bale(1, 5, 4), new Bale(1, 5, 4), new Bale(6, 2, 10));
        Load g = FeedLoft.greedy(bales, 7, 10);
        Load b = FeedLoft.best(bales, 7, 10);
        assertThat(g.bales()).containsExactly(0, 1);
        assertThat(g.nourishment()).isEqualTo(8);
        assertThat(b.bales()).containsExactly(0, 2);
        assertThat(b.nourishment()).isEqualTo(14);
        assertThat(FeedLoft.quest(bales, g.bales(), 7, 10)).isFalse();
    }

    @Test
    void illegalLoadsScoreMinusOne() {
        List<Bale> bales = List.of(new Bale(3, 3, 5), new Bale(4, 1, 6));
        assertThat(FeedLoft.stack(bales, new int[] {0, 0}, 10, 10)).isEqualTo(-1);
        assertThat(FeedLoft.stack(bales, new int[] {2}, 10, 10)).isEqualTo(-1);
        assertThat(FeedLoft.stack(bales, new int[] {0, 1}, 6, 10)).isEqualTo(-1);
        assertThat(FeedLoft.stack(bales, new int[] {0, 1}, 10, 3)).isEqualTo(-1);
        assertThat(FeedLoft.stack(bales, new int[0], 0, 0)).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(FeedLoft.delivery(9, 10, 5)).isEqualTo(FeedLoft.delivery(9, 10, 5));
        assertThat(FeedLoft.best(List.of(), 5, 5).nourishment()).isZero();
        assertThat(FeedLoft.QUEST_ID).isEqualTo("q_full_manger");
        assertThatThrownBy(() -> new Bale(-1, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FeedLoft.delivery(1, -1, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FeedLoft.best(List.of(), -1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(List<Bale> bales, int maxW, int maxB) {
        int best = 0;
        for (int m = 0; m < (1 << bales.size()); m++) {
            int w = 0;
            int k = 0;
            int v = 0;
            for (int i = 0; i < bales.size(); i++) {
                if ((m & (1 << i)) != 0) {
                    w += bales.get(i).weight();
                    k += bales.get(i).bulk();
                    v += bales.get(i).nourishment();
                }
            }
            if (w <= maxW && k <= maxB) {
                best = Math.max(best, v);
            }
        }
        return best;
    }
}
