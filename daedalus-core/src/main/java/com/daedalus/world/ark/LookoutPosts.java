// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Optional;

/**
 * G233 The Lookout Posts: post {@code n} lookouts on the ark's {@code n x n} deck grid so that
 * no two share a row, column or diagonal sightline (N-Queens). A layout is an int[] where
 * {@code cols[r]} is the column of the lookout in row {@code r}. {@link #count} uses bitmask
 * backtracking; {@link #first} returns the lexicographically first layout.
 */
public final class LookoutPosts {

    public static final String QUEST_ID = "q_lookout_posts";
    public static final int MAX_DECK = 16;

    private LookoutPosts() { }

    private static void checkDeck(int n) {
        if (n < 1 || n > MAX_DECK) {
            throw new IllegalArgumentException("deck must be in 1.." + MAX_DECK);
        }
    }

    public static long count(int n) {
        checkDeck(n);
        return count(n, (1 << n) - 1, 0, 0, 0);
    }

    private static long count(int n, int full, int cols, int d1, int d2) {
        if (cols == full) {
            return 1;
        }
        long total = 0;
        int free = full & ~(cols | d1 | d2);
        while (free != 0) {
            int bit = free & -free;
            free ^= bit;
            total += count(n, full, cols | bit, ((d1 | bit) << 1) & full, (d2 | bit) >>> 1);
        }
        return total;
    }

    /** Lexicographically first layout, or empty when none exists. */
    public static Optional<int[]> first(int n) {
        checkDeck(n);
        int[] cols = new int[n];
        return place(n, 0, cols, 0, 0, 0) ? Optional.of(cols) : Optional.empty();
    }

    private static boolean place(int n, int row, int[] out, int cols, int d1, int d2) {
        if (row == n) {
            return true;
        }
        int full = (1 << n) - 1;
        int free = full & ~(cols | d1 | d2);
        while (free != 0) {
            int bit = free & -free;
            free ^= bit;
            out[row] = Integer.numberOfTrailingZeros(bit);
            if (place(n, row + 1, out, cols | bit, ((d1 | bit) << 1) & full, (d2 | bit) >>> 1)) {
                return true;
            }
        }
        return false;
    }

    /** True when {@code cols} posts n lookouts with no shared row, column or diagonal. */
    public static boolean valid(int[] cols) {
        int n = cols.length;
        for (int r = 0; r < n; r++) {
            if (cols[r] < 0 || cols[r] >= n) {
                return false;
            }
            for (int q = 0; q < r; q++) {
                if (cols[q] == cols[r] || Math.abs(cols[q] - cols[r]) == r - q) {
                    return false;
                }
            }
        }
        return n > 0;
    }

    /** Quest q_lookout_posts: the bosun's layout for an n x n deck must be valid. */
    public static boolean quest(int n, int[] cols) {
        checkDeck(n);
        return cols.length == n && valid(cols);
    }
}
