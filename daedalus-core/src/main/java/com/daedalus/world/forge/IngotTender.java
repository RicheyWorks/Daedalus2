// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Ingot Tender (contest gap G281): the island pays in ingots of set weights. Give exact change for a price with the
 * fewest ingots, count every way to make it, and tell whether the greedy biggest-first habit is safe for this set.
 *
 * <p>The tool is plain: {@link #minIngots} and {@link #ways} are O(n * amount) DPs over an {@code int[]} of ingot
 * weights, and {@link #greedyCounterexample} finds the smallest amount where biggest-first fails or uses more ingots
 * (below the sum of the two largest weights when a weight-1 ingot exists, per Kozen and Zaks; otherwise below
 * largest^2 + largest). Any project can use it for change-making.
 */
public final class IngotTender {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ingot_tender";

    /** Returned by {@link #minIngots} when the amount cannot be made. */
    public static final int IMPOSSIBLE = -1;

    /** How a payment went. */
    public enum Grade { EXACT, CLUMSY }

    private IngotTender() {
    }

    /** {@code n} distinct seeded ingot weights in 1..maxWeight, ascending. Same seed, same purse. */
    public static int[] purse(long seed, int n, int maxWeight) {
        if (n < 1 || maxWeight < n) {
            throw new IllegalArgumentException("need 1 <= n <= maxWeight");
        }
        SplittableRandom r = new SplittableRandom(seed);
        boolean[] used = new boolean[maxWeight + 1];
        int[] out = new int[n];
        for (int i = 0; i < n; i++) {
            int w;
            do {
                w = 1 + r.nextInt(maxWeight);
            } while (used[w]);
            used[w] = true;
            out[i] = w;
        }
        Arrays.sort(out);
        return out;
    }

    private static void validate(int[] coins, int amount) {
        if (amount < 0) {
            throw new IllegalArgumentException("need amount >= 0");
        }
        for (int c : coins) {
            if (c < 1) {
                throw new IllegalArgumentException("ingot weights must be >= 1");
            }
        }
    }

    /** Fewest ingots summing to {@code amount}, or {@link #IMPOSSIBLE}. */
    public static int minIngots(int[] coins, int amount) {
        validate(coins, amount);
        int[] dp = new int[amount + 1];
        Arrays.fill(dp, Integer.MAX_VALUE);
        dp[0] = 0;
        for (int a = 1; a <= amount; a++) {
            for (int c : coins) {
                if (c <= a && dp[a - c] != Integer.MAX_VALUE) {
                    dp[a] = Math.min(dp[a], dp[a - c] + 1);
                }
            }
        }
        return dp[amount] == Integer.MAX_VALUE ? IMPOSSIBLE : dp[amount];
    }

    /** Number of unordered ways (multisets of ingots) to make {@code amount}. */
    public static long ways(int[] coins, int amount) {
        validate(coins, amount);
        long[] dp = new long[amount + 1];
        dp[0] = 1;
        for (int c : coins) {
            for (int a = c; a <= amount; a++) {
                dp[a] += dp[a - c];
            }
        }
        return dp[amount];
    }

    /** Ingots used by biggest-first, or {@link #IMPOSSIBLE} if it gets stuck. */
    public static int greedy(int[] coins, int amount) {
        validate(coins, amount);
        int[] sorted = coins.clone();
        Arrays.sort(sorted);
        int left = amount;
        int used = 0;
        for (int i = sorted.length - 1; i >= 0; i--) {
            used += left / sorted[i];
            left %= sorted[i];
        }
        return left == 0 ? used : IMPOSSIBLE;
    }

    /** Smallest amount where biggest-first fails or is beaten, or -1 if biggest-first is always safe. */
    public static int greedyCounterexample(int[] coins) {
        if (coins.length == 0) {
            throw new IllegalArgumentException("need at least one ingot weight");
        }
        int[] sorted = coins.clone();
        Arrays.sort(sorted);
        int n = sorted.length;
        int top = sorted[n - 1];
        int bound;
        if (sorted[0] != 1) {
            bound = top * top + top;
        } else {
            bound = n == 1 ? 2 : top + sorted[n - 2];
        }
        for (int a = 1; a < bound; a++) {
            if (greedy(sorted, a) != minIngots(sorted, a)) {
                return a;
            }
        }
        return -1;
    }

    /** EXACT only if the ingots sum to the price, all come from the purse, and none could be spared. */
    public static Grade grade(int[] coins, int amount, int[] paid) {
        long sum = 0;
        for (int p : paid) {
            if (Arrays.stream(coins).noneMatch(c -> c == p)) {
                return Grade.CLUMSY;
            }
            sum += p;
        }
        return sum == amount && paid.length == minIngots(coins, amount) ? Grade.EXACT : Grade.CLUMSY;
    }

    /** The Forgemaster's line for a payment. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case EXACT -> "Forgemaster: exact, and lighter than any trader could manage. Your purse thanks you.";
            case CLUMSY -> "Forgemaster: wrong sum, or a heavier purse than needed. Weigh it out again.";
        };
    }
}
