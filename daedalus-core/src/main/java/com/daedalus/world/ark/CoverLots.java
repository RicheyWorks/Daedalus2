// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G371 The Cover Lots: the quartermaster has cargo slots 0..m-1 and a list of lots, each lot filling
 * some slots. A packing is exact when every slot is filled by exactly one chosen lot. Knuth's
 * Algorithm X runs on dancing links: each slot is a column of a toroidal linked list, and covering
 * or uncovering a column is a few pointer swaps, always branching on the column with fewest lots.
 */
public final class CoverLots {

    public static final String QUEST_ID = "q_cover_lots";

    private final int[] left;
    private final int[] right;
    private final int[] up;
    private final int[] down;
    private final int[] col;
    private final int[] rowOf;
    private final int[] size;
    private final int[] chosen;
    private int depth;
    private long found;
    private long limit;
    private int[] first = new int[0];

    private CoverLots(int slots, int[][] lots) {
        int nodes = slots + 1;
        for (int[] lot : lots) {
            nodes += lot.length;
        }
        left = new int[nodes];
        right = new int[nodes];
        up = new int[nodes];
        down = new int[nodes];
        col = new int[nodes];
        rowOf = new int[nodes];
        size = new int[slots + 1];
        chosen = new int[lots.length];
        for (int i = 0; i <= slots; i++) {
            left[i] = i == 0 ? slots : i - 1;
            right[i] = i == slots ? 0 : i + 1;
            up[i] = i;
            down[i] = i;
            col[i] = i;
        }
        int next = slots + 1;
        for (int r = 0; r < lots.length; r++) {
            int start = next;
            for (int s : lots[r]) {
                int c = s + 1;
                int x = next++;
                col[x] = c;
                rowOf[x] = r;
                up[x] = up[c];
                down[x] = c;
                down[up[c]] = x;
                up[c] = x;
                size[c]++;
                if (x == start) {
                    left[x] = x;
                    right[x] = x;
                } else {
                    left[x] = left[start];
                    right[x] = start;
                    right[left[start]] = x;
                    left[start] = x;
                }
            }
        }
    }

    private static void check(int slots, int[][] lots) {
        if (slots < 1 || slots > 10_000 || lots.length > 100_000) {
            throw new IllegalArgumentException("slots 1..10000, lots up to 100000");
        }
        for (int[] lot : lots) {
            if (lot.length == 0) {
                throw new IllegalArgumentException("empty lot");
            }
            boolean[] seen = new boolean[slots];
            for (int s : lot) {
                if (s < 0 || s >= slots || seen[s]) {
                    throw new IllegalArgumentException("bad slot " + s);
                }
                seen[s] = true;
            }
        }
    }

    private void cover(int c) {
        right[left[c]] = right[c];
        left[right[c]] = left[c];
        for (int i = down[c]; i != c; i = down[i]) {
            for (int j = right[i]; j != i; j = right[j]) {
                down[up[j]] = down[j];
                up[down[j]] = up[j];
                size[col[j]]--;
            }
        }
    }

    private void uncover(int c) {
        for (int i = up[c]; i != c; i = up[i]) {
            for (int j = left[i]; j != i; j = left[j]) {
                size[col[j]]++;
                down[up[j]] = j;
                up[down[j]] = j;
            }
        }
        right[left[c]] = c;
        left[right[c]] = c;
    }

    private void search() {
        if (found >= limit) {
            return;
        }
        if (right[0] == 0) {
            found++;
            if (found == 1) {
                first = Arrays.copyOf(chosen, depth);
            }
            return;
        }
        int c = right[0];
        for (int j = right[c]; j != 0; j = right[j]) {
            if (size[j] < size[c]) {
                c = j;
            }
        }
        cover(c);
        for (int r = down[c]; r != c; r = down[r]) {
            chosen[depth++] = rowOf[r];
            for (int j = right[r]; j != r; j = right[j]) {
                cover(col[j]);
            }
            search();
            for (int j = left[r]; j != r; j = left[j]) {
                uncover(col[j]);
            }
            depth--;
        }
        uncover(c);
    }

    /** Number of exact packings, stopping at limit. */
    public static long count(int slots, int[][] lots, long limit) {
        check(slots, lots);
        CoverLots x = new CoverLots(slots, lots);
        x.limit = limit;
        x.search();
        return x.found;
    }

    /** Indices of lots in one exact packing (sorted), or an empty array when none exists. */
    public static int[] solve(int slots, int[][] lots) {
        check(slots, lots);
        CoverLots x = new CoverLots(slots, lots);
        x.limit = 1;
        x.search();
        int[] out = x.first.clone();
        Arrays.sort(out);
        return out;
    }

    /** True when the chosen lots fill every slot exactly once. */
    public static boolean isExact(int slots, int[][] lots, int[] pick) {
        int[] hits = new int[slots];
        boolean[] used = new boolean[lots.length];
        for (int p : pick) {
            if (p < 0 || p >= lots.length || used[p]) {
                return false;
            }
            used[p] = true;
            for (int s : lots[p]) {
                if (s < 0 || s >= slots) {
                    return false;
                }
                hits[s]++;
            }
        }
        for (int h : hits) {
            if (h != 1) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_cover_lots: choose lots that fill every slot exactly once. */
    public static boolean quest(int slots, int[][] lots, int[] answer) {
        return isExact(slots, lots, answer);
    }
}