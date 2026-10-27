// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G464 The Cargo Heaps: each hold keeps its crates in a leftist heap keyed by weight, so the
 * quartermaster can add a crate, peek or take the lightest, and pour one hold into another, each
 * in O(log n). Holds are numbered 0 to holds - 1 (1 to 10000 holds); at most 100000 crates are
 * ever added to one fleet. Weights are any long; ties come out in any order.
 */
public final class CargoHeaps {

    public static final String QUEST_ID = "q_cargo_heaps";
    public static final int MAX_HOLDS = 10_000;
    public static final int MAX_CRATES = 100_000;

    private long[] key = new long[16];
    private int[] left = new int[16];
    private int[] right = new int[16];
    private int[] rank = new int[16];
    private int used = 1;
    private final int[] root;
    private final int[] size;

    /** A fleet of empty holds. */
    public CargoHeaps(int holds) {
        if (holds < 1 || holds > MAX_HOLDS) {
            throw new IllegalArgumentException("need 1 to " + MAX_HOLDS + " holds");
        }
        root = new int[holds];
        size = new int[holds];
    }

    private void hold(int h) {
        if (h < 0 || h >= root.length) {
            throw new IllegalArgumentException("no such hold");
        }
    }

    private int meld(int a, int b) {
        if (a == 0) {
            return b;
        }
        if (b == 0) {
            return a;
        }
        int x = a;
        int y = b;
        if (key[y] < key[x]) {
            x = b;
            y = a;
        }
        right[x] = meld(right[x], y);
        if (rank[left[x]] < rank[right[x]]) {
            int t = left[x];
            left[x] = right[x];
            right[x] = t;
        }
        rank[x] = rank[right[x]] + 1;
        return x;
    }

    /** Put a crate of weight w into hold h. */
    public void add(int h, long w) {
        hold(h);
        if (used > MAX_CRATES) {
            throw new IllegalStateException("fleet already took " + MAX_CRATES + " crates");
        }
        if (used == key.length) {
            int c = key.length * 2;
            key = Arrays.copyOf(key, c);
            left = Arrays.copyOf(left, c);
            right = Arrays.copyOf(right, c);
            rank = Arrays.copyOf(rank, c);
        }
        int v = used++;
        key[v] = w;
        rank[v] = 1;
        root[h] = meld(root[h], v);
        size[h]++;
    }

    /** Crates in hold h. */
    public int size(int h) {
        hold(h);
        return size[h];
    }

    /** Lightest crate in hold h; the hold must not be empty. */
    public long lightest(int h) {
        hold(h);
        if (root[h] == 0) {
            throw new IllegalStateException("hold is empty");
        }
        return key[root[h]];
    }

    /** Remove and return the lightest crate in hold h; the hold must not be empty. */
    public long take(int h) {
        long w = lightest(h);
        int r = root[h];
        root[h] = meld(left[r], right[r]);
        size[h]--;
        return w;
    }

    /** Pour every crate of hold from into hold into (from becomes empty). */
    public void pour(int into, int from) {
        hold(into);
        hold(from);
        if (into == from) {
            return;
        }
        root[into] = meld(root[into], root[from]);
        size[into] += size[from];
        root[from] = 0;
        size[from] = 0;
    }

    /**
     * Fleet run: ops are {0, h, w} add, {1, h, 0} take (skipped when empty), {2, into, from} pour.
     * Returns the total weight taken.
     */
    public static long run(int holds, long[][] ops) {
        if (ops == null || ops.length > MAX_CRATES) {
            throw new IllegalArgumentException("at most " + MAX_CRATES + " operations");
        }
        CargoHeaps f = new CargoHeaps(holds);
        long total = 0;
        for (long[] op : ops) {
            if (op == null || op.length != 3 || op[1] < 0 || op[1] >= holds) {
                throw new IllegalArgumentException("ops are {type, hold, value}");
            }
            int h = (int) op[1];
            if (op[0] == 0) {
                f.add(h, op[2]);
            } else if (op[0] == 1) {
                if (f.size(h) > 0) {
                    total += f.take(h);
                }
            } else if (op[0] == 2 && op[2] >= 0 && op[2] < holds) {
                f.pour(h, (int) op[2]);
            } else {
                throw new IllegalArgumentException("unknown op");
            }
        }
        return total;
    }

    /** Quest q_cargo_heaps: the quartermaster names the total weight taken. */
    public static boolean quest(int holds, long[][] ops, long answer) {
        return run(holds, ops) == answer;
    }
}