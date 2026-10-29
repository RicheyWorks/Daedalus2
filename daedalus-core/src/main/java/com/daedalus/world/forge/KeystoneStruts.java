// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Keystone Struts (contest gap G239): the forge roof is a web of joints and two-way struts. Find every keystone joint
 * and every strut whose loss splits the roof.
 *
 * <p>The tool is plain: {@link #keystones} (articulation points) and {@link #bridges} run an iterative Tarjan low-link
 * pass over {@code n} joints and an {@code int[][]} edge list of {u, v} pairs. Parallel struts are handled by edge id,
 * so a doubled strut is never a bridge. Any project can use it for single points of failure in networks.
 */
public final class KeystoneStruts {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_keystone_struts";

    /** How an answer went. */
    public enum Grade { SOUND, CRACKED }

    private KeystoneStruts() {
    }

    /** {@code m} seeded struts between {@code n} joints (no self-loops; parallels allowed). Same seed, same roof. */
    public static int[][] roof(long seed, int n, int m) {
        if ((n < 2 && m > 0) || n < 0 || m < 0) {
            throw new IllegalArgumentException("need n >= 2 for struts and m >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] e = new int[m][];
        for (int i = 0; i < m; i++) {
            int u = r.nextInt(n);
            int v = r.nextInt(n - 1);
            e[i] = new int[] {u, v >= u ? v + 1 : v};
        }
        return e;
    }

    /** Low-link pass; returns {cut flags as 0/1 per joint, bridge flags as 0/1 per edge}. */
    private static int[][] scan(int n, int[][] edges) {
        int m = edges.length;
        int[] deg = new int[n];
        for (int[] e : edges) {
            if (e[0] < 0 || e[0] >= n || e[1] < 0 || e[1] >= n || e[0] == e[1]) {
                throw new IllegalArgumentException("bad strut " + Arrays.toString(e));
            }
            deg[e[0]]++;
            deg[e[1]]++;
        }
        int[][] adj = new int[n][];
        for (int v = 0; v < n; v++) {
            adj[v] = new int[deg[v]];
        }
        int[] fill = new int[n];
        for (int i = 0; i < m; i++) {
            adj[edges[i][0]][fill[edges[i][0]]++] = i;
            adj[edges[i][1]][fill[edges[i][1]]++] = i;
        }
        int[] tin = new int[n];
        int[] low = new int[n];
        Arrays.fill(tin, -1);
        int[] cut = new int[n];
        int[] bridge = new int[m];
        int[] stack = new int[n];
        int[] parentEdge = new int[n];
        int[] next = new int[n];
        int timer = 0;
        for (int root = 0; root < n; root++) {
            if (tin[root] >= 0) {
                continue;
            }
            int sp = 0;
            stack[sp++] = root;
            parentEdge[root] = -1;
            tin[root] = timer;
            low[root] = timer++;
            int rootKids = 0;
            while (sp > 0) {
                int u = stack[sp - 1];
                if (next[u] < adj[u].length) {
                    int id = adj[u][next[u]++];
                    if (id == parentEdge[u]) {
                        continue;
                    }
                    int v = edges[id][0] == u ? edges[id][1] : edges[id][0];
                    if (tin[v] < 0) {
                        tin[v] = timer;
                        low[v] = timer++;
                        parentEdge[v] = id;
                        stack[sp++] = v;
                        if (u == root) {
                            rootKids++;
                        }
                    } else {
                        low[u] = Math.min(low[u], tin[v]);
                    }
                } else {
                    sp--;
                    if (sp > 0) {
                        int p = stack[sp - 1];
                        low[p] = Math.min(low[p], low[u]);
                        if (low[u] > tin[p]) {
                            bridge[parentEdge[u]] = 1;
                        }
                        if (p != root && low[u] >= tin[p]) {
                            cut[p] = 1;
                        }
                    }
                }
            }
            cut[root] = rootKids > 1 ? 1 : 0;
        }
        return new int[][] {cut, bridge};
    }

    private static int[] ones(int[] flags) {
        int[] out = new int[flags.length];
        int c = 0;
        for (int i = 0; i < flags.length; i++) {
            if (flags[i] == 1) {
                out[c++] = i;
            }
        }
        return Arrays.copyOf(out, c);
    }

    /** Keystone joints (articulation points), ascending. */
    public static int[] keystones(int n, int[][] edges) {
        return ones(scan(n, edges)[0]);
    }

    /** Indices into {@code edges} of struts whose loss splits the roof, ascending. */
    public static int[] bridges(int n, int[][] edges) {
        return ones(scan(n, edges)[1]);
    }

    /** SOUND only if both lists are exactly right. */
    public static Grade grade(int n, int[][] edges, int[] keystoneGuess, int[] bridgeGuess) {
        int[][] s = scan(n, edges);
        return Arrays.equals(ones(s[0]), keystoneGuess) && Arrays.equals(ones(s[1]), bridgeGuess)
                ? Grade.SOUND : Grade.CRACKED;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SOUND -> "Forgemaster: every keystone and every lone strut found. The roof will hold.";
            case CRACKED -> "Forgemaster: you missed a weak point. Climb up and look.";
        };
    }
}
