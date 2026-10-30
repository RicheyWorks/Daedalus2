// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.Map;

/**
 * G213 Cork and Wax Budget: the ark's corks, wax, bottles and ark glass are scarce. Choose how
 * many tonics of each G45 tier to bottle, using each tier's {@link Tier#materials()} bill, for
 * the most coin. Exact search over T4/T3/T2 counts with T1 filled last; {@link #greedy} bottles
 * the top tier first and can spend a cork where a cheaper tier would have paid more overall.
 */
public final class CorkWaxBudget {

    public static final String QUEST_ID = "q_cork_and_wax";

    public record Mix(Map<Tier, Integer> counts, int coin, Map<String, Integer> left) {
        public Mix {
            counts = Collections.unmodifiableMap(new EnumMap<>(counts));
            left = Map.copyOf(left);
        }
    }

    private CorkWaxBudget() { }

    /** Most of {@code tier} the stock allows. */
    public static int maxOf(Tier tier, Map<String, Integer> stock) {
        int best = Integer.MAX_VALUE;
        for (Map.Entry<String, Integer> m : tier.materials().entrySet()) {
            best = Math.min(best, stock.getOrDefault(m.getKey(), 0) / m.getValue());
        }
        return best == Integer.MAX_VALUE ? 0 : best;
    }

    /** True when the counts fit the stock. */
    public static boolean fits(Map<Tier, Integer> counts, Map<String, Integer> stock) {
        return left(counts, stock) != null;
    }

    public static Mix best(Map<String, Integer> stock, Map<Tier, Integer> coin) {
        check(stock, coin);
        Mix best = null;
        for (int n4 = 0; n4 <= maxOf(Tier.T4, stock); n4++) {
            Map<String, Integer> s3 = use(stock, Tier.T4, n4);
            for (int n3 = 0; n3 <= maxOf(Tier.T3, s3); n3++) {
                Map<String, Integer> s2 = use(s3, Tier.T3, n3);
                for (int n2 = 0; n2 <= maxOf(Tier.T2, s2); n2++) {
                    Map<String, Integer> s1 = use(s2, Tier.T2, n2);
                    int n1 = coin.getOrDefault(Tier.T1, 0) > 0 ? maxOf(Tier.T1, s1) : 0;
                    Mix m = mix(Map.of(Tier.T1, n1, Tier.T2, n2, Tier.T3, n3, Tier.T4, n4), stock, coin);
                    if (best == null || m.coin() > best.coin()) {
                        best = m;
                    }
                }
            }
        }
        return best;
    }

    /** Naive: bottle as many T4 as possible, then T3, T2, T1. */
    public static Mix greedy(Map<String, Integer> stock, Map<Tier, Integer> coin) {
        check(stock, coin);
        Map<Tier, Integer> counts = new EnumMap<>(Tier.class);
        Map<String, Integer> s = new HashMap<>(stock);
        for (Tier t : new Tier[] {Tier.T4, Tier.T3, Tier.T2, Tier.T1}) {
            int n = maxOf(t, s);
            counts.put(t, n);
            s = use(s, t, n);
        }
        return mix(counts, stock, coin);
    }

    /** Quest q_cork_and_wax: earn at least {@code target} coin from this stock. */
    public static boolean quest(Map<String, Integer> stock, Map<Tier, Integer> coin, int target) {
        return best(stock, coin).coin() >= target;
    }

    private static void check(Map<String, Integer> stock, Map<Tier, Integer> coin) {
        stock.values().forEach(v -> {
            if (v < 0) {
                throw new IllegalArgumentException("negative stock");
            }
        });
        coin.values().forEach(v -> {
            if (v < 0) {
                throw new IllegalArgumentException("negative coin");
            }
        });
    }

    private static Map<String, Integer> use(Map<String, Integer> stock, Tier t, int n) {
        Map<String, Integer> s = new HashMap<>(stock);
        t.materials().forEach((k, q) -> s.merge(k, -q * n, Integer::sum));
        return s;
    }

    private static Map<String, Integer> left(Map<Tier, Integer> counts, Map<String, Integer> stock) {
        Map<String, Integer> s = new HashMap<>(stock);
        for (Map.Entry<Tier, Integer> e : counts.entrySet()) {
            s = use(s, e.getKey(), e.getValue());
        }
        for (int v : s.values()) {
            if (v < 0) {
                return null;
            }
        }
        return s;
    }

    private static Mix mix(Map<Tier, Integer> counts, Map<String, Integer> stock, Map<Tier, Integer> coin) {
        int c = 0;
        for (Map.Entry<Tier, Integer> e : counts.entrySet()) {
            c += e.getValue() * coin.getOrDefault(e.getKey(), 0);
        }
        return new Mix(counts, c, left(counts, stock));
    }
}
