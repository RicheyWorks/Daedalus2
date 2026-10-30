// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Flue Loops (contest gap G236): the forge's one-way flues carry smoke between chambers. Find every group of chambers
 * where smoke can circle back, and how many flues must be added so smoke can reach every chamber from every chamber.
 *
 * <p>The tool is plain: {@link #components} is an iterative Tarjan strongly-connected-components pass over an
 * {@code int[][]} adjacency list, and {@link #fluesToAdd} the classic max(sources, sinks) count on the condensation.
 * Any project can use it for cycle groups in dependency graphs or connectivity repair.
 */
public final class FlueLoops {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_flue_loops";

    /** How an answer went. */
    public enum Grade { CLEAR, SMOKY }

    private FlueLoops() {
    }

    /** {@code n} chambers with each possible one-way flue present with chance pct/100. Same seed, same forge. */
    public static int[][] flues(long seed, int n, int pct) {
        if (n < 0 || pct < 0 || pct > 100) {
            throw new IllegalArgumentException("need n >= 0 and 0 <= pct <= 100");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] adj = new int[n][];
        for (int u = 0; u < n; u++) {
            int[] out = new int[n];
            int c = 0;
            for (int v = 0; v < n; v++) {
                if (v != u && r.nextInt(100) < pct) {
                    out[c++] = v;
                }
            }
            adj[u] = Arrays.copyOf(out, c);
        }
        return adj;
    }

    /** comp[v] = component id of chamber v; ids are 0..k-1 in reverse topological order (sinks first). */
    public static int[] components(int[][] adj) {
        int n = adj.length;
        int[] index = new int[n];
        int[] low = new int[n];
        int[] comp = new int[n];
        boolean[] onStack = new boolean[n];
        Arrays.fill(index, -1);
        int[] stack = new int[n];
        int sp = 0;
        int[] call = new int[n];
        int[] edge = new int[n];
        int counter = 0;
        int k = 0;
        for (int s = 0; s < n; s++) {
            if (index[s] >= 0) {
                continue;
            }
            int cp = 0;
            call[cp++] = s;
            index[s] = counter;
            low[s] = counter++;
            stack[sp++] = s;
            onStack[s] = true;
            edge[s] = 0;
            while (cp > 0) {
                int u = call[cp - 1];
                if (edge[u] < adj[u].length) {
                    int v = adj[u][edge[u]++];
                    if (v < 0 || v >= n) {
                        throw new IllegalArgumentException("flue to missing chamber " + v);
                    }
                    if (index[v] < 0) {
                        index[v] = counter;
                        low[v] = counter++;
                        stack[sp++] = v;
                        onStack[v] = true;
                        edge[v] = 0;
                        call[cp++] = v;
                    } else if (onStack[v]) {
                        low[u] = Math.min(low[u], index[v]);
                    }
                } else {
                    cp--;
                    if (low[u] == index[u]) {
                        int w;
                        do {
                            w = stack[--sp];
                            onStack[w] = false;
                            comp[w] = k;
                        } while (w != u);
                        k++;
                    }
                    if (cp > 0) {
                        int p = call[cp - 1];
                        low[p] = Math.min(low[p], low[u]);
                    }
                }
            }
        }
        return comp;
    }

    /** Number of components. */
    public static int count(int[][] adj) {
        int best = 0;
        for (int c : components(adj)) {
            best = Math.max(best, c + 1);
        }
        return best;
    }

    /** Fewest flues to add so every chamber reaches every other: max(sources, sinks), or 0 with at most one group. */
    public static int fluesToAdd(int[][] adj) {
        int[] comp = components(adj);
        int k = count(adj);
        if (k <= 1) {
            return 0;
        }
        boolean[] hasIn = new boolean[k];
        boolean[] hasOut = new boolean[k];
        for (int u = 0; u < adj.length; u++) {
            for (int v : adj[u]) {
                if (comp[u] != comp[v]) {
                    hasOut[comp[u]] = true;
                    hasIn[comp[v]] = true;
                }
            }
        }
        int sources = 0;
        int sinks = 0;
        for (int c = 0; c < k; c++) {
            sources += hasIn[c] ? 0 : 1;
            sinks += hasOut[c] ? 0 : 1;
        }
        return Math.max(sources, sinks);
    }

    /** CLEAR only if both the loop count and the flues-to-add answer are right. */
    public static Grade grade(int[][] adj, int loops, int toAdd) {
        return loops == count(adj) && toAdd == fluesToAdd(adj) ? Grade.CLEAR : Grade.SMOKY;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case CLEAR -> "Forgemaster: every loop traced and the draught set right. The whole forge breathes as one.";
            case SMOKY -> "Forgemaster: smoke is pooling somewhere you did not look. Trace the flues again.";
        };
    }
}
