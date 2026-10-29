// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G527 The Swell Crests: the lookout logs n wave heights along the ark's wake. The Cartesian tree of the log puts
 * the tallest crest at the root (the leftmost one on ties), with the waves before and after it as its left and right
 * subtrees. It is built in O(n) with a stack. Each crest reigns over the widest window where it is the leftmost
 * tallest wave, which gives how many windows it rules, and the tallest wave in any window is the lowest common
 * ancestor of the window's ends, found in O(log n) by binary lifting.
 *
 * <p>Daedalus hook: the lookout's swell chart on the ark shows a run of waves; quest {@link #QUEST_ID} asks the
 * player which wave crests highest in a shown window ({@link #quest}).
 */
public final class SwellCrests {

    public static final String QUEST_ID = "q_swell_crests";
    /** Most waves the swell chart holds. */
    public static final int MAX_WAVES = 300_000;

    private final int n;
    private final int root;
    private final int[] parent;
    private final int[] left;
    private final int[] right;
    private final int[] spanFrom;
    private final int[] spanTo;
    private final int[] depth;
    private final int[][] up;

    /**
     * Builds the chart for the given wave heights.
     *
     * @throws IllegalArgumentException when there are no waves or more than {@link #MAX_WAVES}
     */
    public SwellCrests(long[] heights) {
        n = heights.length;
        if (n < 1 || n > MAX_WAVES) {
            throw new IllegalArgumentException("need 1.." + MAX_WAVES + " waves");
        }
        parent = new int[n];
        left = new int[n];
        right = new int[n];
        int[] stack = new int[n];
        int top = 0;
        for (int i = 0; i < n; i++) {
            left[i] = -1;
            right[i] = -1;
            int last = -1;
            while (top > 0 && heights[stack[top - 1]] < heights[i]) {
                last = stack[--top];
            }
            left[i] = last;
            if (top > 0) {
                right[stack[top - 1]] = i;
            }
            stack[top++] = i;
        }
        root = stack[0];
        Arrays.fill(parent, -1);
        for (int i = 0; i < n; i++) {
            if (left[i] >= 0) {
                parent[left[i]] = i;
            }
            if (right[i] >= 0) {
                parent[right[i]] = i;
            }
        }
        spanFrom = new int[n];
        spanTo = new int[n];
        depth = new int[n];
        int[] order = new int[n];
        int head = 0;
        int tail = 0;
        order[tail++] = root;
        spanFrom[root] = 0;
        spanTo[root] = n - 1;
        while (head < tail) {
            int v = order[head++];
            if (left[v] >= 0) {
                int c = left[v];
                spanFrom[c] = spanFrom[v];
                spanTo[c] = v - 1;
                depth[c] = depth[v] + 1;
                order[tail++] = c;
            }
            if (right[v] >= 0) {
                int c = right[v];
                spanFrom[c] = v + 1;
                spanTo[c] = spanTo[v];
                depth[c] = depth[v] + 1;
                order[tail++] = c;
            }
        }
        int lg = 1;
        while ((1 << lg) < n) {
            lg++;
        }
        up = new int[lg + 1][n];
        for (int i = 0; i < n; i++) {
            up[0][i] = parent[i] < 0 ? i : parent[i];
        }
        for (int k = 1; k <= lg; k++) {
            for (int i = 0; i < n; i++) {
                up[k][i] = up[k - 1][up[k - 1][i]];
            }
        }
    }

    /** Number of waves. */
    public int size() {
        return n;
    }

    /** Index of the tallest wave (leftmost on ties), the tree root. */
    public int root() {
        return root;
    }

    /** Parent of wave i in the Cartesian tree, or -1 for the root. */
    public int parent(int i) {
        check(i);
        return parent[i];
    }

    /** Left child of wave i, or -1. */
    public int leftChild(int i) {
        check(i);
        return left[i];
    }

    /** Right child of wave i, or -1. */
    public int rightChild(int i) {
        check(i);
        return right[i];
    }

    /** Start of the widest window where wave i is the leftmost tallest. */
    public int reignFrom(int i) {
        check(i);
        return spanFrom[i];
    }

    /** End of the widest window where wave i is the leftmost tallest. */
    public int reignTo(int i) {
        check(i);
        return spanTo[i];
    }

    /** Number of windows [a, b] whose leftmost tallest wave is i. */
    public long windowsRuled(int i) {
        check(i);
        return (long) (i - spanFrom[i] + 1) * (spanTo[i] - i + 1);
    }

    /** Index of the leftmost tallest wave in window [a, b]. */
    public int crest(int a, int b) {
        if (a > b) {
            throw new IllegalArgumentException("need a <= b");
        }
        check(a);
        check(b);
        int x = a;
        int y = b;
        if (depth[x] < depth[y]) {
            int t = x;
            x = y;
            y = t;
        }
        int d = depth[x] - depth[y];
        for (int k = 0; d > 0; k++, d >>= 1) {
            if ((d & 1) != 0) {
                x = up[k][x];
            }
        }
        if (x == y) {
            return x;
        }
        for (int k = up.length - 1; k >= 0; k--) {
            if (up[k][x] != up[k][y]) {
                x = up[k][x];
                y = up[k][y];
            }
        }
        return parent[x];
    }

    /** Quest answer for {@link #QUEST_ID}: which wave crests highest in window [a, b]. */
    public int quest(int a, int b) {
        return crest(a, b);
    }

    private void check(int i) {
        if (i < 0 || i >= n) {
            throw new IllegalArgumentException("no wave " + i);
        }
    }
}
