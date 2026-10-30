// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.CorkWaxBudget.Mix;
import com.daedalus.world.companion.TonicBottler;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.EnumMap;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import org.junit.jupiter.api.Test;

class CorkWaxBudgetTest {

    @Test
    void exactSearchMatchesBruteForce() {
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            Map<String, Integer> stock = randomStock(rnd);
            Map<Tier, Integer> coin = randomCoin(rnd);
            Mix m = CorkWaxBudget.best(stock, coin);
            assertThat(m.coin()).as("seed %d", seed).isEqualTo(brute(stock, coin));
            assertThat(CorkWaxBudget.fits(m.counts(), stock)).isTrue();
        }
    }

    @Test
    void greedyNeverBeatsExactAndSometimesLoses() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            Map<String, Integer> stock = randomStock(rnd);
            Map<Tier, Integer> coin = randomCoin(rnd);
            Mix g = CorkWaxBudget.greedy(stock, coin);
            int exact = CorkWaxBudget.best(stock, coin).coin();
            assertThat(CorkWaxBudget.fits(g.counts(), stock)).isTrue();
            assertThat(exact).isGreaterThanOrEqualTo(g.coin());
            lost |= g.coin() < exact;
        }
        assertThat(lost).isTrue();
    }

    @Test
    void handPickedStockSavesACorkForT2() {
        Map<String, Integer> stock = Map.of(TonicBottler.ARK_GLASS, 1, TonicBottler.BOTTLE, 2,
                TonicBottler.CORK, 2, TonicBottler.WAX, 2);
        Map<Tier, Integer> coin = Map.of(Tier.T1, 1, Tier.T2, 5, Tier.T3, 4, Tier.T4, 12);
        assertThat(CorkWaxBudget.greedy(stock, coin).coin()).isEqualTo(12 + 4 + 1);
        Mix best = CorkWaxBudget.best(stock, coin);
        assertThat(best.coin()).isEqualTo(12 + 5 + 1);
        assertThat(best.counts()).containsEntry(Tier.T4, 1).containsEntry(Tier.T2, 1)
                .containsEntry(Tier.T1, 1).containsEntry(Tier.T3, 0);
    }

    @Test
    void questAndValidation() {
        Map<String, Integer> stock = Map.of(TonicBottler.BOTTLE, 3);
        Map<Tier, Integer> coin = Map.of(Tier.T1, 2);
        assertThat(CorkWaxBudget.quest(stock, coin, 6)).isTrue();
        assertThat(CorkWaxBudget.quest(stock, coin, 7)).isFalse();
        assertThat(CorkWaxBudget.maxOf(Tier.T4, stock)).isZero();
        assertThat(CorkWaxBudget.QUEST_ID).isEqualTo("q_cork_and_wax");
        assertThatThrownBy(() -> CorkWaxBudget.best(Map.of(TonicBottler.CORK, -1), coin))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static Map<String, Integer> randomStock(Random rnd) {
        Map<String, Integer> s = new HashMap<>();
        for (String k : new String[] {TonicBottler.BOTTLE, TonicBottler.CORK, TonicBottler.WAX,
                TonicBottler.ARK_GLASS}) {
            s.put(k, rnd.nextInt(6));
        }
        return s;
    }

    private static Map<Tier, Integer> randomCoin(Random rnd) {
        Map<Tier, Integer> c = new EnumMap<>(Tier.class);
        for (Tier t : Tier.values()) {
            c.put(t, rnd.nextInt(15));
        }
        return c;
    }

    private static int brute(Map<String, Integer> stock, Map<Tier, Integer> coin) {
        int best = 0;
        for (int a = 0; a <= 5; a++) {
            for (int b = 0; b <= 5; b++) {
                for (int c = 0; c <= 5; c++) {
                    for (int d = 0; d <= 5; d++) {
                        Map<Tier, Integer> n = Map.of(Tier.T1, a, Tier.T2, b, Tier.T3, c, Tier.T4, d);
                        if (CorkWaxBudget.fits(n, stock)) {
                            best = Math.max(best, a * coin.get(Tier.T1) + b * coin.get(Tier.T2)
                                    + c * coin.get(Tier.T3) + d * coin.get(Tier.T4));
                        }
                    }
                }
            }
        }
        return best;
    }
}
