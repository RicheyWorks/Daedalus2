// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G569 The Tow Lines: the ark's skiffs ride in a towing forest. Tow lines are tied and cut while the
 * fleet sails, and the bosun asks whether two skiffs are joined and how much load sits on the skiffs
 * along the line path between them (heaviest and total). A link-cut tree (Sleator-Tarjan) answers each
 * tie, cut, load change and path question in amortized O(log n), with splay trees over preferred paths
 * and a lazy flip to re-root. All splaying is iterative, so long chains cannot overflow the stack.
 *
 * <p>Daedalus hook: the bosun's tow board on the ark shows the fleet; quest {@link #QUEST_ID} asks the
 * player for the heaviest skiff on the tow path between two skiffs ({@link #quest}).
 */
public final class TowLines {

    public static final String QUEST_ID = "q_tow_lines";
    /** Most skiffs the tow board holds. */
    public static final int MAX_SKIFFS = 300_000;

    private final int n;
    private final int[] left;
    private final int[] right;
    private final int[] parent;
    private final boolean[] flip;
    private final long[] load;
    private final long[] heaviest;
    private final long[] total;
    private final int[] stack;

    /**
     * Sets up a fleet of skiffs with the given loads and no tow lines.
     *
     * @throws IllegalArgumentException when there are no skiffs or more than {@link #MAX_SKIFFS}
     */
    public TowLines(long[] loads) {
        n = loads.length;
        if (n < 1 || n > MAX_SKIFFS) {
            throw new IllegalArgumentException("need 1.." + MAX_SKIFFS + " skiffs");
        }
        left = new int[n];
        right = new int[n];
        parent = new int[n];
        Arrays.fill(left, -1);
        Arrays.fill(right, -1);
        Arrays.fill(parent, -1);
        flip = new boolean[n];
        load = loads.clone();
        heaviest = loads.clone();
        total = loads.clone();
        stack = new int[n];
    }

    /** Number of skiffs. */
    public int size() {
        return n;
    }

    /** Ties a tow line between two skiffs; false when they are already joined (no loops). */
    public boolean link(int a, int b) {
        check(a);
        check(b);
        if (joined(a, b)) {
            return false;
        }
        makeRoot(a);
        parent[a] = b;
        return true;
    }

    /** Cuts the tow line between two skiffs; false when no such line is tied. */
    public boolean cut(int a, int b) {
        check(a);
        check(b);
        if (a == b) {
            return false;
        }
        makeRoot(a);
        access(b);
        if (left[b] != a || right[a] != -1 || left[a] != -1) {
            return false;
        }
        left[b] = -1;
        parent[a] = -1;
        pull(b);
        return true;
    }

    /** True when the two skiffs are joined by some path of tow lines. */
    public boolean joined(int a, int b) {
        check(a);
        check(b);
        return findRoot(a) == findRoot(b);
    }

    /** Changes the load on one skiff. */
    public void setLoad(int a, long value) {
        check(a);
        access(a);
        load[a] = value;
        pull(a);
    }

    /** Load on one skiff. */
    public long load(int a) {
        check(a);
        return load[a];
    }

    /**
     * Heaviest load on a skiff along the tow path from a to b, both ends included.
     *
     * @throws IllegalArgumentException when the skiffs are not joined
     */
    public long pathMax(int a, int b) {
        exposePath(a, b);
        return heaviest[b];
    }

    /**
     * Total load on the skiffs along the tow path from a to b, both ends included.
     *
     * @throws IllegalArgumentException when the skiffs are not joined
     */
    public long pathSum(int a, int b) {
        exposePath(a, b);
        return total[b];
    }

    /**
     * Quest {@link #QUEST_ID}: ties the given lines in order (lines that would close a loop are left
     * untied) and returns the heaviest skiff load on the path between skiffs a and b, or -1 when they
     * end up not joined.
     */
    public static long quest(long[] loads, int[][] lines, int a, int b) {
        TowLines board = new TowLines(loads);
        for (int[] line : lines) {
            board.link(line[0], line[1]);
        }
        return board.joined(a, b) ? board.pathMax(a, b) : -1L;
    }

    private void exposePath(int a, int b) {
        if (!joined(a, b)) {
            throw new IllegalArgumentException("skiffs " + a + " and " + b + " are not joined");
        }
        makeRoot(a);
        access(b);
    }

    private void check(int a) {
        if (a < 0 || a >= n) {
            throw new IllegalArgumentException("no skiff " + a);
        }
    }

    private boolean isRoot(int x) {
        int p = parent[x];
        return p == -1 || (left[p] != x && right[p] != x);
    }

    private void pull(int x) {
        long m = load[x];
        long s = load[x];
        int l = left[x];
        int r = right[x];
        if (l != -1) {
            m = Math.max(m, heaviest[l]);
            s += total[l];
        }
        if (r != -1) {
            m = Math.max(m, heaviest[r]);
            s += total[r];
        }
        heaviest[x] = m;
        total[x] = s;
    }

    private void push(int x) {
        if (flip[x]) {
            int l = left[x];
            left[x] = right[x];
            right[x] = l;
            if (left[x] != -1) {
                flip[left[x]] ^= true;
            }
            if (right[x] != -1) {
                flip[right[x]] ^= true;
            }
            flip[x] = false;
        }
    }

    private void rotate(int x) {
        int p = parent[x];
        int g = parent[p];
        boolean pRoot = isRoot(p);
        if (left[p] == x) {
            left[p] = right[x];
            if (right[x] != -1) {
                parent[right[x]] = p;
            }
            right[x] = p;
        } else {
            right[p] = left[x];
            if (left[x] != -1) {
                parent[left[x]] = p;
            }
            left[x] = p;
        }
        parent[p] = x;
        parent[x] = g;
        if (!pRoot) {
            if (left[g] == p) {
                left[g] = x;
            } else {
                right[g] = x;
            }
        }
        pull(p);
        pull(x);
    }

    private void splay(int x) {
        int top = 0;
        int y = x;
        stack[top++] = y;
        while (!isRoot(y)) {
            y = parent[y];
            stack[top++] = y;
        }
        while (top > 0) {
            push(stack[--top]);
        }
        while (!isRoot(x)) {
            int p = parent[x];
            if (!isRoot(p)) {
                int g = parent[p];
                boolean zigZig = (left[g] == p) == (left[p] == x);
                rotate(zigZig ? p : x);
            }
            rotate(x);
        }
    }

    private void access(int x) {
        int last = -1;
        for (int y = x; y != -1; y = parent[y]) {
            splay(y);
            right[y] = last;
            pull(y);
            last = y;
        }
        splay(x);
    }

    private void makeRoot(int x) {
        access(x);
        flip[x] ^= true;
        push(x);
    }

    private int findRoot(int x) {
        access(x);
        int y = x;
        push(y);
        while (left[y] != -1) {
            y = left[y];
            push(y);
        }
        splay(y);
        return y;
    }
}
