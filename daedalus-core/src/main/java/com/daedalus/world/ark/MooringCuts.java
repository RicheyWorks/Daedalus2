// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.Arrays;

/**
 * G510 The Mooring Cuts: the ark's flotilla of n islands is tied together by mooring lines, each with a strength.
 * Raiders cutting the ark loose from one island to another must sever lines whose strengths add up to the minimum
 * cut between them. The harbourmaster builds a cut tree (Gomory-Hu, by Gusfield's method with Edmonds-Karp flows):
 * n-1 max-flow runs give the minimum cut for every pair of islands, read off as the weakest edge on the tree path.
 *
 * <p>Daedalus hook: the harbourmaster's chart on the ark names the weakest pair of islands; quest
 * {@link #QUEST_ID} asks the player for the minimum cut between two islands.
 */
public final class MooringCuts {

    public static final String QUEST_ID = "q_mooring_cuts";
    /** Most islands the chart holds. */
    public static final int MAX_ISLANDS = 64;

    private final int n;
    private final int[] parent;
    private final long[] weight;

    /**
     * Builds the cut tree.
     *
     * @param n islands 1..{@link #MAX_ISLANDS}, numbered 0..n-1
     * @param lines mooring lines {a, b, strength} with strength 0 or more; parallel lines add up
     */
    public MooringCuts(int n, int[][] lines) {
        if (n < 1 || n > MAX_ISLANDS) {
            throw new IllegalArgumentException("islands 1.." + MAX_ISLANDS + ": " + n);
        }
        long[][] cap = new long[n][n];
        for (int[] l : lines) {
            if (l.length != 3 || l[0] < 0 || l[0] >= n || l[1] < 0 || l[1] >= n || l[2] < 0) {
                throw new IllegalArgumentException("bad mooring line " + Arrays.toString(l));
            }
            if (l[0] != l[1]) {
                cap[l[0]][l[1]] += l[2];
                cap[l[1]][l[0]] += l[2];
            }
        }
        this.n = n;
        this.parent = new int[n];
        this.weight = new long[n];
        for (int s = 1; s < n; s++) {
            int t = parent[s];
            boolean[] side = new boolean[n];
            weight[s] = maxFlow(cap, s, t, side);
            for (int i = s + 1; i < n; i++) {
                if (side[i] && parent[i] == t) {
                    parent[i] = s;
                }
            }
        }
    }

    /** Edmonds-Karp max flow from s to t; marks the source side of a minimum cut in side. */
    private static long maxFlow(long[][] cap, int s, int t, boolean[] side) {
        int n = cap.length;
        long[][] res = new long[n][];
        for (int i = 0; i < n; i++) {
            res[i] = cap[i].clone();
        }
        long flow = 0;
        int[] from = new int[n];
        while (true) {
            Arrays.fill(from, -1);
            from[s] = s;
            ArrayDeque<Integer> q = new ArrayDeque<>();
            q.add(s);
            while (!q.isEmpty() && from[t] < 0) {
                int u = q.poll();
                for (int v = 0; v < n; v++) {
                    if (from[v] < 0 && res[u][v] > 0) {
                        from[v] = u;
                        q.add(v);
                    }
                }
            }
            if (from[t] < 0) {
                break;
            }
            long push = Long.MAX_VALUE;
            for (int v = t; v != s; v = from[v]) {
                push = Math.min(push, res[from[v]][v]);
            }
            for (int v = t; v != s; v = from[v]) {
                res[from[v]][v] -= push;
                res[v][from[v]] += push;
            }
            flow += push;
        }
        for (int v = 0; v < n; v++) {
            side[v] = from[v] >= 0;
        }
        return flow;
    }

    /** Islands on the chart. */
    public int islands() {
        return n;
    }

    /** Cut-tree parent of each island (island 0 is the root, its own parent), a copy. */
    public int[] parents() {
        return parent.clone();
    }

    /** Weight of the tree edge from each island to its parent (0 for the root), a copy. */
    public long[] weights() {
        return weight.clone();
    }

    private int depth(int v) {
        int d = 0;
        for (int x = v; x != 0; x = parent[x]) {
            d++;
        }
        return d;
    }

    /** Minimum total strength of lines to cut so islands u and v drift apart. */
    public long minCut(int u, int v) {
        if (u < 0 || u >= n || v < 0 || v >= n || u == v) {
            throw new IllegalArgumentException("two different islands 0.." + (n - 1));
        }
        long best = Long.MAX_VALUE;
        int a = u;
        int b = v;
        int da = depth(a);
        int db = depth(b);
        while (a != b) {
            if (da >= db) {
                best = Math.min(best, weight[a]);
                a = parent[a];
                da--;
            } else {
                best = Math.min(best, weight[b]);
                b = parent[b];
                db--;
            }
        }
        return best;
    }

    /** The weakest pair {u, v, cut} on the chart (smallest cut, lowest islands first); needs 2 or more islands. */
    public long[] weakestPair() {
        if (n < 2) {
            throw new IllegalStateException("one island has no pair");
        }
        long[] best = {0, 1, minCut(0, 1)};
        for (int u = 0; u < n; u++) {
            for (int v = u + 1; v < n; v++) {
                long c = minCut(u, v);
                if (c < best[2]) {
                    best = new long[] {u, v, c};
                }
            }
        }
        return best;
    }

    /** Harbourmaster's chart line for the in-world sign. */
    public String chart() {
        if (n < 2) {
            return "The Mooring Cuts: a lone island, nothing to cut.";
        }
        long[] w = weakestPair();
        return "The Mooring Cuts: " + n + " islands; weakest pair " + w[0] + "-" + w[1] + " parts at strength " + w[2]
            + ".";
    }

    /** Quest q_mooring_cuts: the player names the minimum cut between islands u and v. */
    public static boolean quest(int n, int[][] lines, int u, int v, long answer) {
        return new MooringCuts(n, lines).minCut(u, v) == answer;
    }
}