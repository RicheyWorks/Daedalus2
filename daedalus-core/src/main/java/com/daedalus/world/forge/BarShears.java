// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Bar Shears (contest gap G321): a merchant posts prices for iron bar lengths, and each shear cut costs a toll. Cut one
 * bar to earn the most and list the pieces.
 *
 * <p>The tool is plain: rod-cutting DP where {@code price[i]} is the price of a piece of length {@code i + 1}, each cut
 * costs {@code toll}, and the first piece of each optimum is recorded for reconstruction. Any project can use it for
 * cut-stock or bundle pricing.
 */
public final class BarShears {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_bar_shears";

    /** How a cutting went. */
    public enum Grade { PROFIT, SHORTED }

    private BarShears() {
    }

    /** Seeded prices for lengths 1..n, each in [1, maxPrice]. Same seed, same price list. */
    public static long[] prices(long seed, int n, int maxPrice) {
        if (n < 1 || maxPrice < 1) {
            throw new IllegalArgumentException("need n >= 1 and maxPrice >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] p = new long[n];
        for (int i = 0; i < n; i++) {
            p[i] = 1 + r.nextInt(maxPrice);
        }
        return p;
    }

    private static long[][] table(long[] price, int length, long toll) {
        if (length < 1 || length > price.length || toll < 0) {
            throw new IllegalArgumentException("need 1 <= length <= " + price.length + " and toll >= 0");
        }
        long[] best = new long[length + 1];
        long[] first = new long[length + 1];
        for (int l = 1; l <= length; l++) {
            best[l] = Long.MIN_VALUE;
            for (int k = 1; k <= l; k++) {
                long v = price[k - 1] + (k < l ? best[l - k] - toll : 0);
                if (v > best[l]) {
                    best[l] = v;
                    first[l] = k;
                }
            }
        }
        return new long[][] {best, first};
    }

    /** Most a bar of this length can earn after tolls. */
    public static long bestTake(long[] price, int length, long toll) {
        return table(price, length, toll)[0][length];
    }

    /** Piece lengths of one best cutting, in cut order (shortest first piece on ties). */
    public static int[] pieces(long[] price, int length, long toll) {
        long[] first = table(price, length, toll)[1];
        int[] out = new int[length];
        int n = 0;
        int l = length;
        while (l > 0) {
            int k = (int) first[l];
            out[n++] = k;
            l -= k;
        }
        return Arrays.copyOf(out, n);
    }

    /** Earnings of a given cutting after tolls (one toll per cut). */
    public static long take(long[] price, int[] pieces, long toll) {
        long t = 0;
        for (int p : pieces) {
            if (p < 1 || p > price.length) {
                throw new IllegalArgumentException("bad piece length " + p);
            }
            t += price[p - 1];
        }
        return t - toll * Math.max(0, pieces.length - 1);
    }

    /** PROFIT only if the pieces add up to the bar and earn the best take. */
    public static Grade grade(long[] price, int length, long toll, int[] claimed) {
        int sum = 0;
        for (int p : claimed) {
            if (p < 1 || p > price.length) {
                return Grade.SHORTED;
            }
            sum += p;
        }
        return sum == length && take(price, claimed, toll) == bestTake(price, length, toll)
                ? Grade.PROFIT : Grade.SHORTED;
    }

    /** The Forgemaster's line for a cutting. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case PROFIT -> "Forgemaster: not a copper left on the table. The merchant will grumble.";
            case SHORTED -> "Forgemaster: you sold that bar short. Count the tolls and price the pieces again.";
        };
    }
}
