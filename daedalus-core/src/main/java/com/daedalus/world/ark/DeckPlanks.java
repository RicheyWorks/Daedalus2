// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * G335 The Deck Planks: the shipwright covers an m x n deck with 2x1 planks, each lying along or
 * across the deck, no overlaps and no gaps. The count of layouts comes from a broken-profile
 * dynamic program that fills the deck cell by cell, remembering which cells of the next stretch
 * a plank already pokes into.
 */
public final class DeckPlanks {

    public static final String QUEST_ID = "q_deck_planks";

    private DeckPlanks() { }

    /** Number of plank layouts of an m x n deck (m, n from 1; the shorter side at most 12). */
    public static BigInteger count(int m, int n) {
        if (m < 1 || n < 1 || n > 1000 || m > 1000) {
            throw new IllegalArgumentException("deck " + m + "x" + n);
        }
        int rows = Math.min(m, n);
        int cols = Math.max(m, n);
        if (rows > 12) {
            throw new IllegalArgumentException("shorter side at most 12");
        }
        if ((long) rows * cols % 2 != 0) {
            return BigInteger.ZERO;
        }
        int full = 1 << rows;
        BigInteger[] dp = new BigInteger[full];
        Arrays.fill(dp, BigInteger.ZERO);
        dp[0] = BigInteger.ONE;
        for (int c = 0; c < cols; c++) {
            for (int r = 0; r < rows; r++) {
                BigInteger[] nd = new BigInteger[full];
                Arrays.fill(nd, BigInteger.ZERO);
                int bit = 1 << r;
                for (int mask = 0; mask < full; mask++) {
                    BigInteger ways = dp[mask];
                    if (ways.signum() == 0) {
                        continue;
                    }
                    if ((mask & bit) != 0) {
                        nd[mask & ~bit] = nd[mask & ~bit].add(ways);
                        continue;
                    }
                    if (c + 1 < cols) {
                        nd[mask | bit] = nd[mask | bit].add(ways);
                    }
                    if (r + 1 < rows && (mask & (bit << 1)) == 0) {
                        int nm = mask | (bit << 1);
                        nd[nm] = nd[nm].add(ways);
                    }
                }
                dp = nd;
            }
        }
        return dp[0];
    }

    /** True when each plank label covers exactly two edge-adjacent cells and every cell is covered. */
    public static boolean isLayout(int[][] deck) {
        if (deck.length == 0) {
            return false;
        }
        int w = deck[0].length;
        Map<Integer, int[]> seen = new HashMap<>();
        Map<Integer, Integer> size = new HashMap<>();
        for (int r = 0; r < deck.length; r++) {
            if (deck[r].length != w) {
                return false;
            }
            for (int c = 0; c < w; c++) {
                int id = deck[r][c];
                int[] first = seen.putIfAbsent(id, new int[] {r, c});
                int k = size.merge(id, 1, Integer::sum);
                if (k > 2) {
                    return false;
                }
                if (first != null && Math.abs(first[0] - r) + Math.abs(first[1] - c) != 1) {
                    return false;
                }
            }
        }
        for (int k : size.values()) {
            if (k != 2) {
                return false;
            }
        }
        return w > 0;
    }

    /** Quest q_deck_planks: say how many plank layouts the deck has. */
    public static boolean quest(int m, int n, BigInteger answer) {
        return count(m, n).equals(answer);
    }
}