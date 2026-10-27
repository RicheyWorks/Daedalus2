// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G449 The Signal Tree: signals run one way along links {from, to, cost}. The admiral wants the
 * cheapest set of links so the flagship's signal reaches every ship, a minimum spanning
 * arborescence rooted at the flagship. Uses the Chu-Liu/Edmonds method (contract cheapest-in
 * cycles), O(V * E). Up to 200 ships, 20000 links, costs 0 to 10^9; self links are ignored and
 * repeated links are allowed. Returns -1 when some ship cannot be reached.
 */
public final class SignalTree {

    public static final String QUEST_ID = "q_signal_tree";
    public static final int MAX_SHIPS = 200;
    public static final int MAX_LINKS = 20_000;
    public static final long MAX_COST = 1_000_000_000L;

    private SignalTree() { }

    private static void check(int n, int root, long[][] links) {
        if (n < 1 || n > MAX_SHIPS || root < 0 || root >= n) {
            throw new IllegalArgumentException("need 1 to " + MAX_SHIPS + " ships and a flagship among them");
        }
        if (links == null || links.length > MAX_LINKS) {
            throw new IllegalArgumentException("at most " + MAX_LINKS + " links");
        }
        for (long[] e : links) {
            if (e == null || e.length != 3 || e[0] < 0 || e[0] >= n || e[1] < 0 || e[1] >= n
                || e[2] < 0 || e[2] > MAX_COST) {
                throw new IllegalArgumentException("links are {from, to, cost} with cost 0 to 10^9");
            }
        }
    }

    /** Cheapest arborescence cost from the flagship, or -1 when a ship is unreachable. */
    public static long cost(int ships, int flagship, long[][] links) {
        check(ships, flagship, links);
        int m = links.length;
        int[] eu = new int[m];
        int[] ev = new int[m];
        long[] ew = new long[m];
        for (int i = 0; i < m; i++) {
            eu[i] = (int) links[i][0];
            ev[i] = (int) links[i][1];
            ew[i] = links[i][2];
        }
        int n = ships;
        int root = flagship;
        long total = 0;
        while (true) {
            long[] in = new long[n];
            int[] pre = new int[n];
            Arrays.fill(in, Long.MAX_VALUE);
            for (int i = 0; i < m; i++) {
                if (eu[i] != ev[i] && ew[i] < in[ev[i]]) {
                    in[ev[i]] = ew[i];
                    pre[ev[i]] = eu[i];
                }
            }
            for (int v = 0; v < n; v++) {
                if (v != root && in[v] == Long.MAX_VALUE) {
                    return -1;
                }
            }
            in[root] = 0;
            int[] id = new int[n];
            int[] vis = new int[n];
            Arrays.fill(id, -1);
            Arrays.fill(vis, -1);
            int cnt = 0;
            for (int v = 0; v < n; v++) {
                total += in[v];
                int x = v;
                while (vis[x] != v && id[x] == -1 && x != root) {
                    vis[x] = v;
                    x = pre[x];
                }
                if (x != root && id[x] == -1) {
                    for (int y = pre[x]; y != x; y = pre[y]) {
                        id[y] = cnt;
                    }
                    id[x] = cnt++;
                }
            }
            if (cnt == 0) {
                return total;
            }
            for (int v = 0; v < n; v++) {
                if (id[v] == -1) {
                    id[v] = cnt++;
                }
            }
            for (int i = 0; i < m; i++) {
                int v = ev[i];
                eu[i] = id[eu[i]];
                ev[i] = id[v];
                if (eu[i] != ev[i]) {
                    ew[i] -= in[v];
                }
            }
            n = cnt;
            root = id[root];
        }
    }

    /** Quest q_signal_tree: the admiral names the cheapest relay cost (-1 if impossible). */
    public static boolean quest(int ships, int flagship, long[][] links, long answer) {
        return cost(ships, flagship, links) == answer;
    }
}