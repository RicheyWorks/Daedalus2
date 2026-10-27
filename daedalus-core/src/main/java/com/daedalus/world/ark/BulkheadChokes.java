// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G458 The Bulkhead Chokes: a ship's compartments are joined by one-way passages {from, to}. A
 * compartment d dominates v when every route from the bridge to v passes through d; sealing a
 * choke cuts off everything it dominates. Builds the dominator tree (immediate dominators) by the
 * Cooper-Harvey-Kennedy iterative method over reverse postorder. Up to 2000 compartments and
 * 20000 passages. The bridge's immediate dominator is itself; unreachable compartments get -1.
 */
public final class BulkheadChokes {

    public static final String QUEST_ID = "q_bulkhead_chokes";
    public static final int MAX_ROOMS = 2000;
    public static final int MAX_PASSAGES = 20_000;

    private BulkheadChokes() { }

    private static void check(int n, int root, int[][] edges) {
        if (n < 1 || n > MAX_ROOMS || root < 0 || root >= n) {
            throw new IllegalArgumentException("need 1 to " + MAX_ROOMS + " rooms and a bridge among them");
        }
        if (edges == null || edges.length > MAX_PASSAGES) {
            throw new IllegalArgumentException("at most " + MAX_PASSAGES + " passages");
        }
        for (int[] e : edges) {
            if (e == null || e.length != 2 || e[0] < 0 || e[0] >= n || e[1] < 0 || e[1] >= n) {
                throw new IllegalArgumentException("passages are {from, to} room indices");
            }
        }
    }

    private static int[][] adjacency(int n, int[][] edges, boolean reverse) {
        int[] deg = new int[n];
        for (int[] e : edges) {
            deg[reverse ? e[1] : e[0]]++;
        }
        int[][] adj = new int[n][];
        for (int i = 0; i < n; i++) {
            adj[i] = new int[deg[i]];
        }
        Arrays.fill(deg, 0);
        for (int[] e : edges) {
            int a = reverse ? e[1] : e[0];
            adj[a][deg[a]++] = reverse ? e[0] : e[1];
        }
        return adj;
    }

    /** Immediate dominator of every room (bridge maps to itself, unreachable to -1). */
    public static int[] idom(int rooms, int bridge, int[][] passages) {
        check(rooms, bridge, passages);
        int n = rooms;
        int[][] out = adjacency(n, passages, false);
        int[][] in = adjacency(n, passages, true);
        int[] post = new int[n];
        Arrays.fill(post, -1);
        int[] order = new int[n];
        int cnt = 0;
        int[] stack = new int[n];
        int[] it = new int[n];
        boolean[] seen = new boolean[n];
        int sp = 0;
        stack[sp++] = bridge;
        seen[bridge] = true;
        while (sp > 0) {
            int v = stack[sp - 1];
            if (it[v] < out[v].length) {
                int w = out[v][it[v]++];
                if (!seen[w]) {
                    seen[w] = true;
                    stack[sp++] = w;
                }
            } else {
                sp--;
                post[v] = cnt;
                order[cnt++] = v;
            }
        }
        int[] dom = new int[n];
        Arrays.fill(dom, -1);
        dom[bridge] = bridge;
        boolean changed = true;
        while (changed) {
            changed = false;
            for (int k = cnt - 2; k >= 0; k--) {
                int b = order[k];
                int nd = -1;
                for (int p : in[b]) {
                    if (dom[p] == -1) {
                        continue;
                    }
                    nd = nd == -1 ? p : intersect(dom, post, p, nd);
                }
                if (dom[b] != nd) {
                    dom[b] = nd;
                    changed = true;
                }
            }
        }
        return dom;
    }

    private static int intersect(int[] dom, int[] post, int a, int b) {
        int x = a;
        int y = b;
        while (x != y) {
            while (post[x] < post[y]) {
                x = dom[x];
            }
            while (post[y] < post[x]) {
                y = dom[y];
            }
        }
        return x;
    }

    /** Rooms other than the bridge and v itself that lie on every route to v; -1 if unreachable. */
    public static int chokes(int rooms, int bridge, int[][] passages, int v) {
        int[] d = idom(rooms, bridge, passages);
        if (v < 0 || v >= rooms) {
            throw new IllegalArgumentException("no such room");
        }
        if (d[v] == -1) {
            return -1;
        }
        int c = 0;
        for (int x = d[v]; x != bridge; x = d[x]) {
            c++;
        }
        return v == bridge ? 0 : c;
    }

    /** Quest q_bulkhead_chokes: the bosun names how many chokes guard room v. */
    public static boolean quest(int rooms, int bridge, int[][] passages, int v, int answer) {
        return chokes(rooms, bridge, passages, v) == answer;
    }
}