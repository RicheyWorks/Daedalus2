// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.Lot;
import com.daedalus.world.ark.TonicMarket.Port;
import com.daedalus.world.ark.TonicMarket.Result;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.junit.jupiter.api.Test;

class TonicMarketTest {

    @Test
    void greedyMatchesExhaustiveSearch() {
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            List<Port> ports = randomPorts(rnd, 1 + rnd.nextInt(3));
            List<Lot> lots = randomLots(rnd, 1 + rnd.nextInt(6));
            int best = brute(lots, ports, 0, new int[ports.size()][Tier.values().length]);
            assertThat(TonicMarket.sell(lots, ports).coin()).as("seed %d", seed).isEqualTo(best);
        }
    }

    @Test
    void dumpingNeverBeatsTheSplitAndSometimesLoses() {
        boolean lost = false;
        for (long seed = 1; seed <= 200; seed++) {
            Random rnd = new Random(seed);
            List<Port> ports = randomPorts(rnd, 3);
            List<Lot> lots = randomLots(rnd, 10);
            int split = TonicMarket.sell(lots, ports).coin();
            int dump = TonicMarket.dumpAtBestPort(lots, ports).coin();
            assertThat(split).isGreaterThanOrEqualTo(dump);
            lost |= dump < split;
        }
        assertThat(lost).isTrue();
    }

    @Test
    void handPickedLandfallSplitsTheSale() {
        List<Port> ports = List.of(new Port("Cinder Quay", Map.of(Tier.T4, 20), 8),
                new Port("Hull Bay", Map.of(Tier.T4, 15), 0));
        List<Lot> lots = List.of(new Lot(Tier.T4, 0), new Lot(Tier.T4, 0), new Lot(Tier.T4, 0));
        Result r = TonicMarket.sell(lots, ports);
        assertThat(r.coin()).isEqualTo(20 + 15 + 15);
        assertThat(TonicMarket.dumpAtBestPort(lots, ports).coin()).isEqualTo(20 + 12 + 4);
        assertThat(r.sales()).extracting(TonicMarket.Sale::port)
                .containsExactly("Cinder Quay", "Hull Bay", "Hull Bay");
    }

    @Test
    void questAndValidation() {
        List<Port> ports = List.of(new Port("Cinder Quay", Map.of(Tier.T1, 3), 1));
        List<Lot> lots = List.of(new Lot(Tier.T1, 0), new Lot(Tier.T1, 0));
        assertThat(TonicMarket.quest(lots, ports, 5)).isTrue();
        assertThat(TonicMarket.quest(lots, ports, 6)).isFalse();
        assertThat(TonicMarket.QUEST_ID).isEqualTo("q_tonic_market");
        assertThat(ports.get(0).price(Tier.T1, 10)).isZero();
        assertThat(ports.get(0).price(Tier.T4, 0)).isZero();
        assertThatThrownBy(() -> TonicMarket.sell(lots, List.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Port("x", Map.of(Tier.T1, -1), 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void sellsARealArkCellarShelf() {
        ArkCellar cellar = new ArkCellar(ArkCellar.Rules.defaults());
        ArkCellar.State s = cellar.day(cellar.start(300), 0,
                new ArkCellar.Day(false, Map.of(Tier.T2, 3, Tier.T4, 2))).state();
        List<Port> ports = List.of(new Port("Cinder Quay", Map.of(Tier.T2, 6, Tier.T4, 18), 3));
        Result r = TonicMarket.sell(s.cellar(), ports);
        assertThat(r.sales()).hasSize(5);
        assertThat(r.coin()).isEqualTo(6 + 3 + 0 + 18 + 15);
    }

    private static List<Port> randomPorts(Random rnd, int n) {
        List<Port> ports = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            Map<Tier, Integer> base = new EnumMap<>(Tier.class);
            for (Tier t : Tier.values()) {
                base.put(t, rnd.nextInt(25));
            }
            ports.add(new Port("port" + i, base, rnd.nextInt(6)));
        }
        return ports;
    }

    private static List<Lot> randomLots(Random rnd, int n) {
        List<Lot> lots = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            lots.add(new Lot(Tier.values()[rnd.nextInt(4)], 0));
        }
        return lots;
    }

    private static int brute(List<Lot> lots, List<Port> ports, int i, int[][] sold) {
        if (i == lots.size()) {
            return 0;
        }
        int t = lots.get(i).tier().ordinal();
        int best = Integer.MIN_VALUE;
        for (int p = 0; p < ports.size(); p++) {
            int price = ports.get(p).price(lots.get(i).tier(), sold[p][t]);
            sold[p][t]++;
            best = Math.max(best, price + brute(lots, ports, i + 1, sold));
            sold[p][t]--;
        }
        return best;
    }
}
