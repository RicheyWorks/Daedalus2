// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.ark.ArkCellar.Lot;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * G208 Tonic Market at Landfall: sell the G196 cellar across the ports of a landfall.
 *
 * <p>Each port pays {@code basePrice(tier) - drop * j} coin (never below zero) for its
 * {@code j}-th bottle of that tier. Each (port, tier) price run only falls, so handing every
 * bottle to the port that pays most for its next sale is optimal; {@link #dumpAtBestPort}
 * is the naive habit of selling everything at the port with the highest base price.
 */
public final class TonicMarket {

    public static final String QUEST_ID = "q_tonic_market";

    public record Port(String name, Map<Tier, Integer> basePrice, int drop) {
        public Port {
            Objects.requireNonNull(name);
            if (drop < 0) {
                throw new IllegalArgumentException("drop < 0");
            }
            EnumMap<Tier, Integer> p = new EnumMap<>(Tier.class);
            for (Map.Entry<Tier, Integer> e : basePrice.entrySet()) {
                if (e.getValue() < 0) {
                    throw new IllegalArgumentException("price < 0");
                }
                p.put(e.getKey(), e.getValue());
            }
            basePrice = Collections.unmodifiableMap(p);
        }

        /** Price of the {@code j}-th (0-based) sale of {@code tier} here. */
        public int price(Tier tier, int j) {
            return Math.max(0, basePrice.getOrDefault(tier, 0) - drop * j);
        }
    }

    public record Sale(Lot lot, String port, int coin) { }

    public record Result(int coin, List<Sale> sales) {
        public Result {
            sales = List.copyOf(sales);
        }
    }

    private TonicMarket() { }

    /** Optimal split: each bottle goes where its next sale pays most (ties: earlier port). */
    public static Result sell(List<Lot> lots, List<Port> ports) {
        if (ports.isEmpty()) {
            throw new IllegalArgumentException("no ports");
        }
        Map<String, int[]> sold = new HashMap<>();
        List<Sale> sales = new ArrayList<>();
        int coin = 0;
        for (Lot lot : lots) {
            Port best = null;
            int bestPrice = -1;
            for (Port p : ports) {
                int j = sold.computeIfAbsent(p.name(), k -> new int[Tier.values().length])[lot.tier().ordinal()];
                int price = p.price(lot.tier(), j);
                if (price > bestPrice) {
                    best = p;
                    bestPrice = price;
                }
            }
            sold.get(best.name())[lot.tier().ordinal()]++;
            sales.add(new Sale(lot, best.name(), bestPrice));
            coin += bestPrice;
        }
        return new Result(coin, sales);
    }

    /** Naive: sell everything at the port with the highest base price for the lot's tier. */
    public static Result dumpAtBestPort(List<Lot> lots, List<Port> ports) {
        if (ports.isEmpty()) {
            throw new IllegalArgumentException("no ports");
        }
        int[][] sold = new int[ports.size()][Tier.values().length];
        List<Sale> sales = new ArrayList<>();
        int coin = 0;
        for (Lot lot : lots) {
            int bi = 0;
            for (int i = 1; i < ports.size(); i++) {
                if (ports.get(i).basePrice().getOrDefault(lot.tier(), 0)
                        > ports.get(bi).basePrice().getOrDefault(lot.tier(), 0)) {
                    bi = i;
                }
            }
            int price = ports.get(bi).price(lot.tier(), sold[bi][lot.tier().ordinal()]++);
            sales.add(new Sale(lot, ports.get(bi).name(), price));
            coin += price;
        }
        return new Result(coin, sales);
    }

    /** Quest q_tonic_market: earn at least {@code target} coin from the cellar at this landfall. */
    public static boolean quest(List<Lot> lots, List<Port> ports, int target) {
        return sell(lots, ports).coin() >= target;
    }
}
