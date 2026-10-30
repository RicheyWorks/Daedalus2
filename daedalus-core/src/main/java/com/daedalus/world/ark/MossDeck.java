// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;

/**
 * G243 The Moss Deck: storm moss spreads across the ark's wrap-around (toroidal) deck by Conway's
 * Life rules, B3/S23. {@link #step} grows one night, {@link #cycle} finds when the deck first
 * repeats and its period, and {@link #after} forecasts night k by jumping through the cycle.
 * Decks are {@code boolean[rows][cols]}, true = moss; inputs are never modified.
 */
public final class MossDeck {

    public static final String QUEST_ID = "q_moss_deck";

    /** The deck first seen at night {@code start} recurs every {@code period} nights. */
    public record Cycle(int start, int period) { }

    private MossDeck() { }

    public static boolean[][] step(boolean[][] deck) {
        check(deck);
        int rows = deck.length;
        int cols = deck[0].length;
        boolean[][] next = new boolean[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int n = neighbours(deck, r, c);
                next[r][c] = n == 3 || (n == 2 && deck[r][c]);
            }
        }
        return next;
    }

    /** Live neighbours of (r, c) with wrap-around; on tiny decks a cell may be counted twice. */
    static int neighbours(boolean[][] deck, int r, int c) {
        int rows = deck.length;
        int cols = deck[0].length;
        int n = 0;
        for (int dr = -1; dr <= 1; dr++) {
            for (int dc = -1; dc <= 1; dc++) {
                if ((dr != 0 || dc != 0) && deck[(r + dr + rows) % rows][(c + dc + cols) % cols]) {
                    n++;
                }
            }
        }
        return n;
    }

    /** First repeated deck within {@code maxNights} nights, or null if none seen. */
    public static Cycle cycle(boolean[][] deck, int maxNights) {
        check(deck);
        Map<String, Integer> seen = new HashMap<>();
        boolean[][] cur = copy(deck);
        for (int night = 0; night <= maxNights; night++) {
            Integer first = seen.putIfAbsent(key(cur), night);
            if (first != null) {
                return new Cycle(first, night - first);
            }
            cur = step(cur);
        }
        return null;
    }

    /** The deck after {@code k} nights; uses the cycle to skip ahead when one appears. */
    public static boolean[][] after(boolean[][] deck, long k) {
        check(deck);
        if (k < 0) {
            throw new IllegalArgumentException("k < 0");
        }
        Map<String, Integer> seen = new HashMap<>();
        boolean[][] cur = copy(deck);
        long night = 0;
        while (night < k) {
            Integer first = seen.putIfAbsent(key(cur), (int) night);
            if (first != null) {
                long period = night - first;
                long remaining = (k - night) % period;
                for (long i = 0; i < remaining; i++) {
                    cur = step(cur);
                }
                return cur;
            }
            if (seen.size() > 1_000_000) {
                seen.clear();
            }
            cur = step(cur);
            night++;
        }
        return cur;
    }

    public static int moss(boolean[][] deck) {
        int n = 0;
        for (boolean[] row : deck) {
            for (boolean b : row) {
                if (b) {
                    n++;
                }
            }
        }
        return n;
    }

    /** Parses rows like {@code ".#."}; '#' is moss. */
    public static boolean[][] parse(String... rows) {
        if (rows.length == 0) {
            throw new IllegalArgumentException("empty deck");
        }
        boolean[][] d = new boolean[rows.length][];
        for (int r = 0; r < rows.length; r++) {
            d[r] = new boolean[rows[r].length()];
            for (int c = 0; c < rows[r].length(); c++) {
                d[r][c] = rows[r].charAt(c) == '#';
            }
        }
        check(d);
        return d;
    }

    /** Quest q_moss_deck: the bosun's forecast for night k must match the deck exactly. */
    public static boolean quest(boolean[][] deck, long k, boolean[][] forecast) {
        boolean[][] truth = after(deck, k);
        if (forecast.length != truth.length) {
            return false;
        }
        for (int r = 0; r < truth.length; r++) {
            if (!java.util.Arrays.equals(truth[r], forecast[r])) {
                return false;
            }
        }
        return true;
    }

    private static String key(boolean[][] d) {
        StringBuilder sb = new StringBuilder(d.length * d[0].length);
        for (boolean[] row : d) {
            for (boolean b : row) {
                sb.append(b ? '1' : '0');
            }
        }
        return sb.toString();
    }

    private static boolean[][] copy(boolean[][] d) {
        boolean[][] c = new boolean[d.length][];
        for (int r = 0; r < d.length; r++) {
            c[r] = d[r].clone();
        }
        return c;
    }

    private static void check(boolean[][] d) {
        if (d == null || d.length == 0 || d[0] == null || d[0].length == 0) {
            throw new IllegalArgumentException("empty deck");
        }
        for (boolean[] row : d) {
            if (row == null || row.length != d[0].length) {
                throw new IllegalArgumentException("ragged deck");
            }
        }
    }
}
