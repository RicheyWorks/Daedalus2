// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Crucible Loads (contest gap G189): the forge smelts the salvage pulled out of the Meteor Scar ({@link ScarDig}) in
 * crucibles that each hold a fixed weight. Every lump goes whole into one crucible, and every firing burns charcoal, so
 * fewer crucibles is better.
 *
 * <p>The packer is deliberately plain: weights are an {@code int[]}, a packing is a list of crucibles, each a list of
 * lump indices. Any project can call {@link #pack} or {@link #optimal} for cargo holds, save chunks or inventory pages.
 *
 * <p>Rules: {@link Rule#NEXT_FIT} keeps one crucible open and closes it when a lump does not fit (never more than
 * 2 OPT - 1), {@link Rule#FIRST_FIT} puts each lump in the first crucible with room, and
 * {@link Rule#FIRST_FIT_DECREASING} does the same heaviest lump first (never more than 11/9 OPT + 6/9).
 * {@link #optimal} finds the true fewest crucibles exactly by branch and bound.
 */
public final class CrucibleLoads {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_crucible_loads";
    /** Largest haul {@link #optimal} accepts; the search is exponential in the worst case. */
    public static final int MAX_EXACT_LUMPS = 24;

    /** How lumps are loaded. */
    public enum Rule { NEXT_FIT, FIRST_FIT, FIRST_FIT_DECREASING }

    /** How a firing compares with the fewest possible crucibles. */
    public enum Grade { WARM, SMOKY, WASTEFUL }

    /** A haul of salvage lumps and the crucible size. */
    public record Haul(int capacity, List<Integer> lumps) {

        public Haul {
            if (capacity <= 0) {
                throw new IllegalArgumentException("capacity must be positive");
            }
            lumps = List.copyOf(lumps);
            for (int w : lumps) {
                if (w <= 0 || w > capacity) {
                    throw new IllegalArgumentException("lump weight out of range: " + w);
                }
            }
        }

        /** The weights as a fresh array. */
        public int[] weights() {
            int[] w = new int[lumps.size()];
            for (int i = 0; i < w.length; i++) {
                w[i] = lumps.get(i);
            }
            return w;
        }

        /** Sum lower bound: no packing uses fewer crucibles than ceil(total / capacity). */
        public int lowerBound() {
            long total = 0;
            for (int w : lumps) {
                total += w;
            }
            return (int) ((total + capacity - 1) / capacity);
        }
    }

    /** One firing: the packing (lump indices per crucible), the true fewest crucibles and the grade. */
    public record Firing(Rule rule, List<List<Integer>> crucibles, int fewest, Grade grade) {

        public Firing {
            List<List<Integer>> copy = new ArrayList<>();
            for (List<Integer> c : crucibles) {
                copy.add(List.copyOf(c));
            }
            crucibles = List.copyOf(copy);
        }

        /** Crucibles used. */
        public int used() {
            return crucibles.size();
        }
    }

    private CrucibleLoads() {
    }

    /** A seeded haul: {@code n} lumps with weights in [1, capacity]. Same seed, same haul. */
    public static Haul haul(long seed, int n, int capacity) {
        if (n < 0 || capacity <= 0) {
            throw new IllegalArgumentException("n must be >= 0 and capacity positive");
        }
        SplittableRandom r = new SplittableRandom(seed);
        List<Integer> l = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            l.add(1 + r.nextInt(capacity));
        }
        return new Haul(capacity, l);
    }

    /** Packs {@code weights} into crucibles of {@code capacity} by {@code rule}; returns lump indices per crucible. */
    public static List<List<Integer>> pack(int[] weights, int capacity, Rule rule) {
        check(weights, capacity);
        Integer[] order = new Integer[weights.length];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        if (rule == Rule.FIRST_FIT_DECREASING) {
            Arrays.sort(order, (a, b) -> weights[b] != weights[a]
                    ? Integer.compare(weights[b], weights[a]) : Integer.compare(a, b));
        }
        List<List<Integer>> bins = new ArrayList<>();
        List<Integer> load = new ArrayList<>();
        for (int i : order) {
            int w = weights[i];
            int at = -1;
            if (rule == Rule.NEXT_FIT) {
                int last = bins.size() - 1;
                if (last >= 0 && load.get(last) + w <= capacity) {
                    at = last;
                }
            } else {
                for (int b = 0; b < bins.size(); b++) {
                    if (load.get(b) + w <= capacity) {
                        at = b;
                        break;
                    }
                }
            }
            if (at < 0) {
                bins.add(new ArrayList<>());
                load.add(0);
                at = bins.size() - 1;
            }
            bins.get(at).add(i);
            load.set(at, load.get(at) + w);
        }
        return bins;
    }

    /** The true fewest crucibles for {@code weights}, by branch and bound (at most {@value #MAX_EXACT_LUMPS} lumps). */
    public static int optimal(int[] weights, int capacity) {
        check(weights, capacity);
        if (weights.length > MAX_EXACT_LUMPS) {
            throw new IllegalArgumentException("too many lumps for the exact solver: " + weights.length);
        }
        if (weights.length == 0) {
            return 0;
        }
        int[] w = weights.clone();
        Arrays.sort(w);
        for (int i = 0, j = w.length - 1; i < j; i++, j--) {
            int t = w[i];
            w[i] = w[j];
            w[j] = t;
        }
        long total = 0;
        for (int x : w) {
            total += x;
        }
        int lb = (int) ((total + capacity - 1) / capacity);
        int[] best = {pack(w, capacity, Rule.FIRST_FIT).size()};
        if (best[0] > lb) {
            search(w, capacity, 0, new int[w.length], 0, total, lb, best);
        }
        return best[0];
    }

    private static void search(int[] w, int cap, int i, int[] load, int open, long left, int lb, int[] best) {
        if (best[0] == lb) {
            return;
        }
        if (i == w.length) {
            best[0] = Math.min(best[0], open);
            return;
        }
        long free = 0;
        for (int b = 0; b < open; b++) {
            free += cap - load[b];
        }
        long extra = left - free;
        int need = open + (extra > 0 ? (int) ((extra + cap - 1) / cap) : 0);
        if (need >= best[0]) {
            return;
        }
        for (int b = 0; b < open; b++) {
            if (load[b] + w[i] > cap || sameLoadEarlier(load, b)) {
                continue;
            }
            load[b] += w[i];
            search(w, cap, i + 1, load, open, left - w[i], lb, best);
            load[b] -= w[i];
        }
        if (open + 1 < best[0]) {
            load[open] = w[i];
            search(w, cap, i + 1, load, open + 1, left - w[i], lb, best);
            load[open] = 0;
        }
    }

    private static boolean sameLoadEarlier(int[] load, int b) {
        for (int c = 0; c < b; c++) {
            if (load[c] == load[b]) {
                return true;
            }
        }
        return false;
    }

    /** Fires a haul by a rule and grades it against the fewest possible crucibles. */
    public static Firing fire(Haul haul, Rule rule) {
        int[] w = haul.weights();
        List<List<Integer>> bins = pack(w, haul.capacity(), rule);
        int fewest = optimal(w, haul.capacity());
        return new Firing(rule, bins, fewest, grade(bins.size(), fewest));
    }

    /** WARM at the fewest, SMOKY one over, WASTEFUL beyond. */
    public static Grade grade(int used, int fewest) {
        if (used < fewest) {
            throw new IllegalArgumentException("used below the optimum");
        }
        if (used == fewest) {
            return Grade.WARM;
        }
        return used == fewest + 1 ? Grade.SMOKY : Grade.WASTEFUL;
    }

    /** The Forgemaster's line for a firing. */
    public static String forgemasterLine(Firing f) {
        return switch (f.grade()) {
            case WARM -> "Forgemaster: " + f.used() + " crucibles, not one more. The charcoal thanks you.";
            case SMOKY -> "Forgemaster: " + f.used() + " crucibles. One fewer would have done. Heaviest first.";
            case WASTEFUL -> "Forgemaster: " + f.used() + " crucibles for a " + f.fewest()
                    + "-crucible haul. The whole shop is coughing.";
        };
    }

    private static void check(int[] weights, int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        for (int x : weights) {
            if (x <= 0 || x > capacity) {
                throw new IllegalArgumentException("lump weight out of range: " + x);
            }
        }
    }
}
