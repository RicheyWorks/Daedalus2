// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.ark.ArkCellar.Lot;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * G211 Hold Stowage: choose which G196 cellar bottles ride the landfall boat in one crate with a
 * weight limit, for the most coin. Exact 0/1 knapsack DP over integer weights; {@link #greedy}
 * is the coin-per-weight habit, which can leave a better pair of bottles on the shelf.
 */
public final class HoldStowage {

    public static final String QUEST_ID = "q_hold_stowage";

    /** Coin and weight (integer units) per bottle of each tier. */
    public record Prices(Map<Tier, Integer> coin, Map<Tier, Integer> weight) {
        public Prices {
            EnumMap<Tier, Integer> c = new EnumMap<>(Tier.class);
            EnumMap<Tier, Integer> w = new EnumMap<>(Tier.class);
            for (Tier t : Tier.values()) {
                int ci = coin.getOrDefault(t, 0);
                Integer wi = weight.get(t);
                if (ci < 0 || wi == null || wi <= 0) {
                    throw new IllegalArgumentException("bad price/weight for " + t);
                }
                c.put(t, ci);
                w.put(t, wi);
            }
            coin = Collections.unmodifiableMap(c);
            weight = Collections.unmodifiableMap(w);
        }

        /** Ark-glass T4 is heavy and dear; plain T1 light and cheap. */
        public static Prices defaults() {
            return new Prices(Map.of(Tier.T1, 2, Tier.T2, 4, Tier.T3, 7, Tier.T4, 15),
                    Map.of(Tier.T1, 3, Tier.T2, 4, Tier.T3, 5, Tier.T4, 9));
        }
    }

    public record Result(int coin, int weight, List<Lot> stowed) {
        public Result {
            stowed = List.copyOf(stowed);
        }
    }

    private HoldStowage() { }

    public static Result stow(List<Lot> lots, Prices p, int capacity) {
        if (capacity < 0) {
            throw new IllegalArgumentException("capacity < 0");
        }
        int n = lots.size();
        int[][] best = new int[n + 1][capacity + 1];
        for (int i = 1; i <= n; i++) {
            Tier t = lots.get(i - 1).tier();
            int w = p.weight().get(t);
            int c = p.coin().get(t);
            for (int cap = 0; cap <= capacity; cap++) {
                best[i][cap] = best[i - 1][cap];
                if (w <= cap) {
                    best[i][cap] = Math.max(best[i][cap], best[i - 1][cap - w] + c);
                }
            }
        }
        List<Lot> chosen = new ArrayList<>();
        int cap = capacity;
        for (int i = n; i >= 1; i--) {
            if (best[i][cap] != best[i - 1][cap]) {
                Lot l = lots.get(i - 1);
                chosen.add(l);
                cap -= p.weight().get(l.tier());
            }
        }
        Collections.reverse(chosen);
        return result(chosen, p);
    }

    /** Naive: highest coin per weight first, take whatever still fits. */
    public static Result greedy(List<Lot> lots, Prices p, int capacity) {
        if (capacity < 0) {
            throw new IllegalArgumentException("capacity < 0");
        }
        List<Lot> order = new ArrayList<>(lots);
        order.sort(Comparator.comparingDouble(
                (Lot l) -> -(double) p.coin().get(l.tier()) / p.weight().get(l.tier())));
        List<Lot> chosen = new ArrayList<>();
        int left = capacity;
        for (Lot l : order) {
            int w = p.weight().get(l.tier());
            if (w <= left) {
                chosen.add(l);
                left -= w;
            }
        }
        return result(chosen, p);
    }

    /** Quest q_hold_stowage: stow at least {@code target} coin in one crate. */
    public static boolean quest(List<Lot> lots, Prices p, int capacity, int target) {
        return stow(lots, p, capacity).coin() >= target;
    }

    private static Result result(List<Lot> chosen, Prices p) {
        int coin = 0;
        int weight = 0;
        for (Lot l : chosen) {
            coin += p.coin().get(l.tier());
            weight += p.weight().get(l.tier());
        }
        return new Result(coin, weight, chosen);
    }
}
