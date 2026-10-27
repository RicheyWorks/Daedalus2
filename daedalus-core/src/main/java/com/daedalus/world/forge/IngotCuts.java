// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Ingot Cuts (contest gap G190): the forge draws one long bar from each {@link CrucibleLoads} firing, and the quay buys
 * ingots by length. Cut the bar into whole-unit ingots to fetch the most scrip; every saw cut costs a kerf fee.
 *
 * <p>The cutter is plain: {@code prices[len]} is what an ingot of length {@code len} fetches
 * ({@code prices[0]} unused), a cut plan is the list of ingot lengths. Any project can call
 * {@link #best} for cargo splits or timeline chunks.
 * {@link #best} is the exact rod-cutting DP; {@link #greedy} takes the best price per unit first and can lose.
 */
public final class IngotCuts {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ingot_cuts";
    /** Longest bar the forge draws. */
    public static final int MAX_BAR = 20;
    /** Bar units drawn per crucible fired. */
    public static final int UNITS_PER_CRUCIBLE = 3;

    /** How a cut compares with the best. */
    public enum Grade { MASTERWORK, FAIR, SCRAP }

    /** A cut plan: ingot lengths in cutting order and the scrip it fetches after kerf fees. */
    public record Cut(List<Integer> pieces, int value) {

        public Cut {
            pieces = List.copyOf(pieces);
        }
    }

    private IngotCuts() {
    }

    /** Bar length drawn from a firing: {@value #UNITS_PER_CRUCIBLE} units per crucible, at most {@value #MAX_BAR}. */
    public static int barFrom(CrucibleLoads.Firing firing) {
        return Math.min(MAX_BAR, firing.used() * UNITS_PER_CRUCIBLE);
    }

    /** Seeded quay prices for lengths 1..n: roughly 3 scrip a unit with a seeded premium or discount. */
    public static int[] quayPrices(long seed, int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] p = new int[n + 1];
        for (int len = 1; len <= n; len++) {
            p[len] = Math.max(1, 3 * len + r.nextInt(-len, 2 * len + 1));
        }
        return p;
    }

    /** Scrip a plan fetches: the ingot prices less {@code kerf} per cut (pieces - 1 cuts). */
    public static int value(int[] prices, int kerf, List<Integer> pieces) {
        if (pieces.isEmpty()) {
            return 0;
        }
        int v = 0;
        for (int len : pieces) {
            if (len < 1 || len >= prices.length) {
                throw new IllegalArgumentException("ingot length out of range: " + len);
            }
            v += prices[len];
        }
        return v - kerf * (pieces.size() - 1);
    }

    /** The exact best cut of a bar of length {@code n} (rod-cutting DP; ties keep the fewest, longest-first pieces). */
    public static Cut best(int[] prices, int n, int kerf) {
        check(prices, n, kerf);
        if (n == 0) {
            return new Cut(List.of(), 0);
        }
        int[] f = new int[n + 1];
        int[] first = new int[n + 1];
        for (int len = 1; len <= n; len++) {
            f[len] = prices[len];
            first[len] = len;
            for (int i = len - 1; i >= 1; i--) {
                int v = prices[i] + f[len - i] - kerf;
                if (v > f[len]) {
                    f[len] = v;
                    first[len] = i;
                }
            }
        }
        List<Integer> pieces = new ArrayList<>();
        for (int left = n; left > 0; left -= first[left]) {
            pieces.add(first[left]);
        }
        return new Cut(pieces, f[n]);
    }

    /** Greedy: keep cutting the length with the best price per unit that still fits (longer wins ties). */
    public static Cut greedy(int[] prices, int n, int kerf) {
        check(prices, n, kerf);
        List<Integer> pieces = new ArrayList<>();
        int left = n;
        while (left > 0) {
            int pick = 1;
            for (int len = 2; len <= left; len++) {
                if ((long) prices[len] * pick >= (long) prices[pick] * len) {
                    pick = len;
                }
            }
            pieces.add(pick);
            left -= pick;
        }
        return new Cut(pieces, value(prices, kerf, pieces));
    }

    /** MASTERWORK at the best, FAIR at 90% or more of it, SCRAP below. */
    public static Grade grade(int value, int best) {
        if (value > best) {
            throw new IllegalArgumentException("value above the best");
        }
        if (value == best) {
            return Grade.MASTERWORK;
        }
        return 10L * value >= 9L * best ? Grade.FAIR : Grade.SCRAP;
    }

    /** The Forgemaster's line for a cut. */
    public static String forgemasterLine(Cut cut, int best) {
        return switch (grade(cut.value(), best)) {
            case MASTERWORK -> "Forgemaster: " + cut.value() + " scrip. Not a shaving wasted.";
            case FAIR -> "Forgemaster: " + cut.value() + " of " + best + " scrip. Close. Measure twice.";
            case SCRAP -> "Forgemaster: " + cut.value() + " of " + best + " scrip. That bar deserved better.";
        };
    }

    private static void check(int[] prices, int n, int kerf) {
        if (n < 0 || n >= prices.length) {
            throw new IllegalArgumentException("bar length out of range: " + n);
        }
        if (kerf < 0) {
            throw new IllegalArgumentException("kerf must be >= 0");
        }
    }
}
