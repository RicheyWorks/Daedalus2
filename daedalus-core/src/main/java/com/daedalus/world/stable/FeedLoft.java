// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;

/**
 * G516 The Feed Loft (Studio horse lane): before winter the stable hand stacks hay bales in the
 * loft. Each bale has a weight, a bulk (volume) and a nourishment value; the loft floor holds at
 * most {@code maxWeight} and the loft space at most {@code maxBulk}. {@link #best} picks the set of
 * bales with the most nourishment that respects both limits, with an exact two-constraint 0/1
 * dynamic program; {@link #greedy} (stack the best nourishment-per-weight bales first) is the habit
 * that fills the loft with light, bulky bales and runs out of space. Plain int[] API.
 */
public final class FeedLoft {

    public static final String QUEST_ID = "q_full_manger";

    /** A bale: weight, bulk and nourishment (all non-negative). */
    public record Bale(int weight, int bulk, int nourishment) {
        public Bale {
            if (weight < 0 || bulk < 0 || nourishment < 0) {
                throw new IllegalArgumentException("bad bale");
            }
        }
    }

    /** A loaded loft: total nourishment and the chosen bale indices in ascending order. */
    public record Load(int nourishment, int[] bales) {
        public Load {
            bales = bales.clone();
        }

        @Override
        public int[] bales() {
            return bales.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Load l && l.nourishment == nourishment && Arrays.equals(l.bales, bales);
        }

        @Override
        public int hashCode() {
            return 31 * nourishment + Arrays.hashCode(bales);
        }

        @Override
        public String toString() {
            return "Load[" + nourishment + ", " + Arrays.toString(bales) + "]";
        }
    }

    private FeedLoft() { }

    /** Seeded delivery of {@code n} bales with weight and bulk in [1, maxSize], nourishment in [1, 20]. */
    public static List<Bale> delivery(long seed, int n, int maxSize) {
        if (n < 0 || maxSize <= 0) {
            throw new IllegalArgumentException("bad delivery");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        List<Bale> out = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            out.add(new Bale(1 + rnd.nextInt(maxSize), 1 + rnd.nextInt(maxSize), 1 + rnd.nextInt(20)));
        }
        return List.copyOf(out);
    }

    /** Most nourishing load within both limits (exact DP over bale, weight, bulk). */
    public static Load best(List<Bale> bales, int maxWeight, int maxBulk) {
        checkLimits(maxWeight, maxBulk);
        int n = bales.size();
        int[][][] v = new int[n + 1][maxWeight + 1][maxBulk + 1];
        for (int i = 1; i <= n; i++) {
            Bale b = bales.get(i - 1);
            for (int w = 0; w <= maxWeight; w++) {
                for (int k = 0; k <= maxBulk; k++) {
                    int skip = v[i - 1][w][k];
                    int take = -1;
                    if (b.weight() <= w && b.bulk() <= k) {
                        take = v[i - 1][w - b.weight()][k - b.bulk()] + b.nourishment();
                    }
                    v[i][w][k] = Math.max(skip, take);
                }
            }
        }
        List<Integer> chosen = new ArrayList<>();
        int w = maxWeight;
        int k = maxBulk;
        for (int i = n; i >= 1; i--) {
            if (v[i][w][k] != v[i - 1][w][k]) {
                Bale b = bales.get(i - 1);
                chosen.add(0, i - 1);
                w -= b.weight();
                k -= b.bulk();
            }
        }
        return new Load(v[n][maxWeight][maxBulk], chosen.stream().mapToInt(Integer::intValue).toArray());
    }

    /** Naive: take bales by nourishment per unit weight (ties by index) while both limits allow. */
    public static Load greedy(List<Bale> bales, int maxWeight, int maxBulk) {
        checkLimits(maxWeight, maxBulk);
        Integer[] order = new Integer[bales.size()];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        Comparator<Integer> byRatio = (a, b) -> {
            Bale x = bales.get(a);
            Bale y = bales.get(b);
            long lhs = (long) y.nourishment() * Math.max(1, x.weight());
            long rhs = (long) x.nourishment() * Math.max(1, y.weight());
            int c = Long.compare(lhs, rhs);
            return c != 0 ? c : Integer.compare(a, b);
        };
        Arrays.sort(order, byRatio);
        int w = 0;
        int k = 0;
        int total = 0;
        List<Integer> chosen = new ArrayList<>();
        for (int idx : order) {
            Bale b = bales.get(idx);
            if (w + b.weight() <= maxWeight && k + b.bulk() <= maxBulk) {
                w += b.weight();
                k += b.bulk();
                total += b.nourishment();
                chosen.add(idx);
            }
        }
        return new Load(total, chosen.stream().sorted().mapToInt(Integer::intValue).toArray());
    }

    /** Nourishment of a stacked load, or -1 when indices repeat, are out of range or break a limit. */
    public static int stack(List<Bale> bales, int[] chosen, int maxWeight, int maxBulk) {
        checkLimits(maxWeight, maxBulk);
        boolean[] used = new boolean[bales.size()];
        int w = 0;
        int k = 0;
        int total = 0;
        for (int idx : chosen) {
            if (idx < 0 || idx >= bales.size() || used[idx]) {
                return -1;
            }
            used[idx] = true;
            Bale b = bales.get(idx);
            w += b.weight();
            k += b.bulk();
            total += b.nourishment();
        }
        return w <= maxWeight && k <= maxBulk ? total : -1;
    }

    /** Quest q_full_manger: the stable hand's load is legal and as nourishing as possible. */
    public static boolean quest(List<Bale> bales, int[] chosen, int maxWeight, int maxBulk) {
        int got = stack(bales, chosen, maxWeight, maxBulk);
        return got >= 0 && got == best(bales, maxWeight, maxBulk).nourishment();
    }

    private static void checkLimits(int maxWeight, int maxBulk) {
        if (maxWeight < 0 || maxBulk < 0) {
            throw new IllegalArgumentException("bad loft");
        }
    }
}
