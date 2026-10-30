// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Guild Lineage (contest gap G244): every smith on the island trained under one master, forming a lineage tree. For any
 * two smiths name their nearest shared master and how many teaching steps apart they are.
 *
 * <p>The tool is plain: binary-lifting lowest common ancestor over an {@code int[]} parent array ({@code -1} marks a
 * founder; a forest is allowed), with O(n log n) build and O(log n) {@link #lca}, {@link #kthAncestor} and
 * {@link #distance}. Any project can use it for hierarchy queries.
 */
public final class GuildLineage {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_guild_lineage";

    /** How an answer went. */
    public enum Grade { KIN, STRANGER }

    private final int[][] up;
    private final int[] depth;
    private final int[] founder;

    /** Builds the lineage; rejects out-of-range parents and cycles. */
    public GuildLineage(int[] parent) {
        int n = parent.length;
        int[] childCount = new int[n];
        for (int v = 0; v < n; v++) {
            int p = parent[v];
            if (p < -1 || p >= n || p == v) {
                throw new IllegalArgumentException("bad master " + p + " for smith " + v);
            }
            if (p >= 0) {
                childCount[p]++;
            }
        }
        int[][] kids = new int[n][];
        for (int v = 0; v < n; v++) {
            kids[v] = new int[childCount[v]];
        }
        int[] fill = new int[n];
        for (int v = 0; v < n; v++) {
            if (parent[v] >= 0) {
                kids[parent[v]][fill[parent[v]]++] = v;
            }
        }
        int levels = 1;
        while ((1 << levels) < Math.max(1, n)) {
            levels++;
        }
        up = new int[levels][n];
        depth = new int[n];
        founder = new int[n];
        int[] queue = new int[n];
        int head = 0;
        int tail = 0;
        for (int v = 0; v < n; v++) {
            if (parent[v] < 0) {
                queue[tail++] = v;
                founder[v] = v;
            }
        }
        while (head < tail) {
            int u = queue[head++];
            for (int c : kids[u]) {
                depth[c] = depth[u] + 1;
                founder[c] = founder[u];
                queue[tail++] = c;
            }
        }
        if (tail != n) {
            throw new IllegalArgumentException("lineage has a cycle");
        }
        for (int v = 0; v < n; v++) {
            up[0][v] = parent[v] < 0 ? v : parent[v];
        }
        for (int k = 1; k < levels; k++) {
            for (int v = 0; v < n; v++) {
                up[k][v] = up[k - 1][up[k - 1][v]];
            }
        }
    }

    /** A seeded lineage of {@code n} smiths: smith 0 founds it and each later smith trains under an earlier one. */
    public static int[] lineage(long seed, int n) {
        if (n < 0) {
            throw new IllegalArgumentException("need n >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] p = new int[n];
        for (int v = 0; v < n; v++) {
            p[v] = v == 0 ? -1 : r.nextInt(v);
        }
        return p;
    }

    private void check(int v) {
        if (v < 0 || v >= depth.length) {
            throw new IllegalArgumentException("no smith " + v);
        }
    }

    /** Teaching steps from smith {@code v} up to its founder. */
    public int depth(int v) {
        check(v);
        return depth[v];
    }

    /** The master {@code k} steps above {@code v}, or -1 if that climbs past the founder. */
    public int kthAncestor(int v, int k) {
        check(v);
        if (k < 0) {
            throw new IllegalArgumentException("need k >= 0");
        }
        if (k > depth[v]) {
            return -1;
        }
        int x = v;
        int rem = k;
        int b = 0;
        while (rem > 0) {
            if ((rem & 1) == 1) {
                x = up[b][x];
            }
            rem >>= 1;
            b++;
        }
        return x;
    }

    /** Nearest shared master (a smith counts as their own), or -1 if they descend from different founders. */
    public int lca(int a, int b) {
        check(a);
        check(b);
        if (founder[a] != founder[b]) {
            return -1;
        }
        int x = depth[a] >= depth[b] ? a : b;
        int y = x == a ? b : a;
        x = kthAncestor(x, depth[x] - depth[y]);
        if (x == y) {
            return x;
        }
        for (int k = up.length - 1; k >= 0; k--) {
            if (up[k][x] != up[k][y]) {
                x = up[k][x];
                y = up[k][y];
            }
        }
        return up[0][x];
    }

    /** Teaching steps between two smiths, or -1 if they share no founder. */
    public int distance(int a, int b) {
        int m = lca(a, b);
        return m < 0 ? -1 : depth[a] + depth[b] - 2 * depth[m];
    }

    /** KIN only if both the shared master and the distance are right. */
    public Grade grade(int a, int b, int master, int steps) {
        return lca(a, b) == master && distance(a, b) == steps ? Grade.KIN : Grade.STRANGER;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case KIN -> "Forgemaster: you know the guild's bloodlines by heart. Those two will drink together tonight.";
            case STRANGER -> "Forgemaster: that is not who taught them. Read the guild rolls again.";
        };
    }
}
