// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.PriorityQueue;

/**
 * G515 The Knot Codes: the bosun writes every rigging of n spars (a labelled tree, spars 0..n-1) in the log as its
 * Pruefer code, n-2 spar numbers. Encoding repeatedly cuts the lowest-numbered leaf and writes down its neighbour;
 * decoding rebuilds the one tree with that code. Both run in O(n log n) with a heap. Codes also rank to a single
 * number 0..n^(n-2)-1, so the log can name "rigging number r".
 *
 * <p>Daedalus hook: the bosun's knot board shows a rigging and its code; quest {@link #QUEST_ID} asks the player to
 * write the code for a shown rigging.
 */
public final class KnotCodes {

    public static final String QUEST_ID = "q_knot_codes";
    /** Most spars the knot board holds. */
    public static final int MAX_SPARS = 100_000;

    private KnotCodes() { }

    private static void checkN(int n) {
        if (n < 2 || n > MAX_SPARS) {
            throw new IllegalArgumentException("spars 2.." + MAX_SPARS + ": " + n);
        }
    }

    /** Pruefer code of the tree with these n-1 lines {a, b}; throws when the lines are not a tree on n spars. */
    public static int[] encode(int n, int[][] lines) {
        checkN(n);
        if (lines.length != n - 1) {
            throw new IllegalArgumentException("a rigging of " + n + " spars has " + (n - 1) + " lines");
        }
        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            adj.add(new ArrayList<>());
        }
        int[] degree = new int[n];
        for (int[] l : lines) {
            if (l.length != 2 || l[0] < 0 || l[0] >= n || l[1] < 0 || l[1] >= n || l[0] == l[1]) {
                throw new IllegalArgumentException("bad line " + Arrays.toString(l));
            }
            adj.get(l[0]).add(l[1]);
            adj.get(l[1]).add(l[0]);
            degree[l[0]]++;
            degree[l[1]]++;
        }
        PriorityQueue<Integer> leaves = new PriorityQueue<>();
        for (int v = 0; v < n; v++) {
            if (degree[v] == 1) {
                leaves.add(v);
            }
        }
        boolean[] cut = new boolean[n];
        int[] code = new int[n - 2];
        for (int k = 0; k < n - 2; k++) {
            if (leaves.isEmpty()) {
                throw new IllegalArgumentException("lines hold a loop, not a rigging");
            }
            int leaf = leaves.poll();
            cut[leaf] = true;
            int nb = -1;
            for (int u : adj.get(leaf)) {
                if (!cut[u]) {
                    nb = u;
                }
            }
            if (nb < 0) {
                throw new IllegalArgumentException("lines do not hold every spar together");
            }
            code[k] = nb;
            degree[nb]--;
            if (degree[nb] == 1) {
                leaves.add(nb);
            }
        }
        int left = 0;
        for (int v = 0; v < n; v++) {
            if (!cut[v]) {
                left++;
                if (degree[v] != 1) {
                    throw new IllegalArgumentException("lines are not a rigging");
                }
            }
        }
        if (left != 2) {
            throw new IllegalArgumentException("lines are not a rigging");
        }
        return code;
    }

    /** The rigging with this code, lines {a, b} with a &lt; b, sorted. */
    public static int[][] decode(int n, int[] code) {
        checkN(n);
        if (code.length != n - 2) {
            throw new IllegalArgumentException("code for " + n + " spars has " + (n - 2) + " numbers");
        }
        int[] degree = new int[n];
        Arrays.fill(degree, 1);
        for (int c : code) {
            if (c < 0 || c >= n) {
                throw new IllegalArgumentException("spar out of range: " + c);
            }
            degree[c]++;
        }
        PriorityQueue<Integer> leaves = new PriorityQueue<>();
        for (int v = 0; v < n; v++) {
            if (degree[v] == 1) {
                leaves.add(v);
            }
        }
        int[][] out = new int[n - 1][];
        for (int k = 0; k < n - 2; k++) {
            int leaf = leaves.poll();
            int c = code[k];
            out[k] = new int[] {Math.min(leaf, c), Math.max(leaf, c)};
            degree[c]--;
            if (degree[c] == 1) {
                leaves.add(c);
            }
        }
        int a = leaves.poll();
        int b = leaves.poll();
        out[n - 2] = new int[] {Math.min(a, b), Math.max(a, b)};
        Arrays.sort(out, (x, y) -> x[0] != y[0] ? Integer.compare(x[0], y[0]) : Integer.compare(x[1], y[1]));
        return out;
    }

    /** Rigging number of a code, its value in base n; needs n^(n-2) to fit a long. */
    public static long rank(int n, int[] code) {
        checkN(n);
        long r = 0;
        for (int c : code) {
            if (c < 0 || c >= n) {
                throw new IllegalArgumentException("spar out of range: " + c);
            }
            r = Math.addExact(Math.multiplyExact(r, n), c);
        }
        return r;
    }

    /** Code of rigging number r on n spars. */
    public static int[] unrank(int n, long r) {
        checkN(n);
        int[] code = new int[n - 2];
        long x = r;
        if (x < 0) {
            throw new IllegalArgumentException("negative rigging number");
        }
        for (int k = n - 3; k >= 0; k--) {
            code[k] = (int) (x % n);
            x /= n;
        }
        if (x != 0) {
            throw new IllegalArgumentException("rigging number too large");
        }
        return code;
    }

    /** Knot board sign text. */
    public static String board(int n, int[][] lines) {
        return "The Knot Codes: " + n + " spars, code " + Arrays.toString(encode(n, lines)) + ".";
    }

    /** Quest q_knot_codes: the player writes the code for the shown rigging. */
    public static boolean quest(int n, int[][] lines, int[] answer) {
        return answer != null && Arrays.equals(encode(n, lines), answer);
    }
}