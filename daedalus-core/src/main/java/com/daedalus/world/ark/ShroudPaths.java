// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G520 The Shroud Paths: the ark's rigging is a tree of n spars joined by shroud lines, and each spar carries a
 * strain reading. The rigger asks for the heaviest strain and the total strain on the path between two spars, while
 * the bosun re-tensions single spars. A heavy-light decomposition cuts the tree into O(log n) chains on any path, and
 * one segment tree over the chain order answers each query in O(log^2 n) and each re-tension in O(log n).
 *
 * <p>Daedalus hook: the rigger's tally board on the ark shows the strain path between two spars; quest
 * {@link #QUEST_ID} asks the player for the heaviest strain on a shown path ({@link #quest}).
 */
public final class ShroudPaths {

    public static final String QUEST_ID = "q_shroud_paths";
    /** Most spars the tally board holds. */
    public static final int MAX_SPARS = 200_000;

    private final int n;
    private final int[] parent;
    private final int[] depth;
    private final int[] head;
    private final int[] pos;
    private final int size;
    private final long[] mx;
    private final long[] sm;

    /**
     * Builds the board for spars 0..n-1 joined by n-1 lines {a, b} forming a tree, with each spar's strain.
     *
     * @throws IllegalArgumentException when the lines are not a tree on n spars or strain has the wrong length
     */
    public ShroudPaths(int n, int[][] lines, long[] strain) {
        if (n < 1 || n > MAX_SPARS || lines.length != n - 1 || strain.length != n) {
            throw new IllegalArgumentException("need 1.." + MAX_SPARS + " spars, n-1 lines and n strains");
        }
        this.n = n;
        int[] deg = new int[n];
        for (int[] l : lines) {
            if (l.length != 2 || l[0] < 0 || l[1] < 0 || l[0] >= n || l[1] >= n || l[0] == l[1]) {
                throw new IllegalArgumentException("bad line " + Arrays.toString(l));
            }
            deg[l[0]]++;
            deg[l[1]]++;
        }
        int[] start = new int[n + 1];
        for (int i = 0; i < n; i++) {
            start[i + 1] = start[i] + deg[i];
        }
        int[] adj = new int[2 * (n - 1)];
        int[] fill = Arrays.copyOf(start, n);
        for (int[] l : lines) {
            adj[fill[l[0]]++] = l[1];
            adj[fill[l[1]]++] = l[0];
        }
        parent = new int[n];
        depth = new int[n];
        Arrays.fill(parent, -2);
        parent[0] = -1;
        int[] order = new int[n];
        int seen = 1;
        for (int i = 0; i < seen; i++) {
            int v = order[i];
            for (int k = start[v]; k < start[v + 1]; k++) {
                int w = adj[k];
                if (parent[w] == -2) {
                    parent[w] = v;
                    depth[w] = depth[v] + 1;
                    order[seen++] = w;
                }
            }
        }
        if (seen != n) {
            throw new IllegalArgumentException("lines do not join every spar");
        }
        int[] sub = new int[n];
        int[] heavy = new int[n];
        Arrays.fill(heavy, -1);
        for (int i = n - 1; i >= 0; i--) {
            int v = order[i];
            sub[v]++;
            int p = parent[v];
            if (p >= 0) {
                sub[p] += sub[v];
                if (heavy[p] < 0 || sub[v] > sub[heavy[p]]) {
                    heavy[p] = v;
                }
            }
        }
        head = new int[n];
        pos = new int[n];
        int next = 0;
        for (int i = 0; i < n; i++) {
            int v = order[i];
            if (parent[v] >= 0 && heavy[parent[v]] == v) {
                continue;
            }
            for (int u = v; u >= 0; u = heavy[u]) {
                head[u] = v;
                pos[u] = next++;
            }
        }
        int s = 1;
        while (s < n) {
            s <<= 1;
        }
        size = s;
        mx = new long[2 * s];
        sm = new long[2 * s];
        Arrays.fill(mx, Long.MIN_VALUE);
        for (int v = 0; v < n; v++) {
            mx[s + pos[v]] = strain[v];
            sm[s + pos[v]] = strain[v];
        }
        for (int i = s - 1; i >= 1; i--) {
            mx[i] = Math.max(mx[2 * i], mx[2 * i + 1]);
            sm[i] = sm[2 * i] + sm[2 * i + 1];
        }
    }

    private void check(int v) {
        if (v < 0 || v >= n) {
            throw new IllegalArgumentException("no spar " + v);
        }
    }

    /** Number of spars. */
    public int spars() {
        return n;
    }

    /** Current strain on spar v. */
    public long strain(int v) {
        check(v);
        return sm[size + pos[v]];
    }

    /** Re-tensions spar v to the given strain. */
    public void set(int v, long value) {
        check(v);
        int i = size + pos[v];
        mx[i] = value;
        sm[i] = value;
        for (i >>= 1; i >= 1; i >>= 1) {
            mx[i] = Math.max(mx[2 * i], mx[2 * i + 1]);
            sm[i] = sm[2 * i] + sm[2 * i + 1];
        }
    }

    /** {max, sum} over chain positions lo..hi inclusive. */
    private long[] range(int lo, int hi) {
        long m = Long.MIN_VALUE;
        long t = 0;
        for (int l = lo + size, r = hi + size + 1; l < r; l >>= 1, r >>= 1) {
            if ((l & 1) != 0) {
                m = Math.max(m, mx[l]);
                t += sm[l++];
            }
            if ((r & 1) != 0) {
                m = Math.max(m, mx[--r]);
                t += sm[r];
            }
        }
        return new long[] {m, t};
    }

    private long[] path(int a, int b) {
        check(a);
        check(b);
        long m = Long.MIN_VALUE;
        long t = 0;
        int u = a;
        int v = b;
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) {
                int x = u;
                u = v;
                v = x;
            }
            long[] r = range(pos[head[u]], pos[u]);
            m = Math.max(m, r[0]);
            t += r[1];
            u = parent[head[u]];
        }
        long[] r = range(Math.min(pos[u], pos[v]), Math.max(pos[u], pos[v]));
        return new long[] {Math.max(m, r[0]), t + r[1], depth[u] < depth[v] ? u : v};
    }

    /** Heaviest strain on the path between spars a and b, both ends included. */
    public long pathMax(int a, int b) {
        return path(a, b)[0];
    }

    /** Total strain on the path between spars a and b, both ends included. */
    public long pathSum(int a, int b) {
        return path(a, b)[1];
    }

    /** The spar where the paths from a and b to spar 0 meet. */
    public int meet(int a, int b) {
        return (int) path(a, b)[2];
    }

    /** Spars on the path between a and b, both ends included. */
    public int pathLength(int a, int b) {
        int m = meet(a, b);
        return depth[a] + depth[b] - 2 * depth[m] + 1;
    }

    /** Quest q_shroud_paths: the player's answer must be the heaviest strain between a and b. */
    public static boolean quest(ShroudPaths board, int a, int b, long answer) {
        return board != null && board.pathMax(a, b) == answer;
    }
}
