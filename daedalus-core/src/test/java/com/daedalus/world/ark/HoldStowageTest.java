// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.Lot;
import com.daedalus.world.ark.HoldStowage.Prices;
import com.daedalus.world.ark.HoldStowage.Result;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.junit.jupiter.api.Test;

class HoldStowageTest {

    @Test
    void dpMatchesExhaustiveSearch() {
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            Prices p = randomPrices(rnd);
            List<Lot> lots = randomLots(rnd, 1 + rnd.nextInt(10));
            int cap = rnd.nextInt(40);
            Result r = HoldStowage.stow(lots, p, cap);
            assertThat(r.coin()).as("seed %d", seed).isEqualTo(brute(lots, p, cap));
            assertThat(r.weight()).isLessThanOrEqualTo(cap);
        }
    }

    @Test
    void greedyNeverBeatsDpAndSometimesLoses() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            Prices p = randomPrices(rnd);
            List<Lot> lots = randomLots(rnd, 8);
            int cap = 5 + rnd.nextInt(30);
            int dp = HoldStowage.stow(lots, p, cap).coin();
            Result g = HoldStowage.greedy(lots, p, cap);
            assertThat(g.weight()).isLessThanOrEqualTo(cap);
            assertThat(dp).isGreaterThanOrEqualTo(g.coin());
            lost |= g.coin() < dp;
        }
        assertThat(lost).isTrue();
    }

    @Test
    void handPickedCrateLeavesTheArkGlassBehind() {
        Prices p = new Prices(Map.of(Tier.T1, 1, Tier.T2, 1, Tier.T3, 8, Tier.T4, 10),
                Map.of(Tier.T1, 1, Tier.T2, 1, Tier.T3, 5, Tier.T4, 6));
        List<Lot> lots = List.of(new Lot(Tier.T4, 0), new Lot(Tier.T3, 0), new Lot(Tier.T3, 1));
        Result dp = HoldStowage.stow(lots, p, 10);
        assertThat(dp.coin()).isEqualTo(16);
        assertThat(dp.stowed()).extracting(Lot::tier).containsExactly(Tier.T3, Tier.T3);
        assertThat(HoldStowage.greedy(lots, p, 10).coin()).isEqualTo(10);
    }

    @Test
    void questDefaultsAndValidation() {
        ArkCellar cellar = new ArkCellar(ArkCellar.Rules.defaults());
        List<Lot> shelf = cellar.day(cellar.start(300), 0,
                new ArkCellar.Day(false, Map.of(Tier.T1, 2, Tier.T4, 2))).state().cellar();
        Prices p = Prices.defaults();
        assertThat(HoldStowage.quest(shelf, p, 18, 30)).isTrue();
        assertThat(HoldStowage.quest(shelf, p, 17, 30)).isFalse();
        assertThat(HoldStowage.stow(shelf, p, 0).stowed()).isEmpty();
        assertThat(HoldStowage.QUEST_ID).isEqualTo("q_hold_stowage");
        assertThatThrownBy(() -> HoldStowage.stow(shelf, p, -1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Prices(Map.of(), Map.of(Tier.T1, 1)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static Prices randomPrices(Random rnd) {
        Map<Tier, Integer> c = new EnumMap<>(Tier.class);
        Map<Tier, Integer> w = new EnumMap<>(Tier.class);
        for (Tier t : Tier.values()) {
            c.put(t, rnd.nextInt(20));
            w.put(t, 1 + rnd.nextInt(10));
        }
        return new Prices(c, w);
    }

    private static List<Lot> randomLots(Random rnd, int n) {
        List<Lot> lots = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            lots.add(new Lot(Tier.values()[rnd.nextInt(4)], i));
        }
        return lots;
    }

    private static int brute(List<Lot> lots, Prices p, int cap) {
        int best = 0;
        for (int mask = 0; mask < (1 << lots.size()); mask++) {
            int w = 0;
            int c = 0;
            for (int i = 0; i < lots.size(); i++) {
                if ((mask & (1 << i)) != 0) {
                    w += p.weight().get(lots.get(i).tier());
                    c += p.coin().get(lots.get(i).tier());
                }
            }
            if (w <= cap) {
                best = Math.max(best, c);
            }
        }
        return best;
    }
}
