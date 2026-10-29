// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.OptionalLong;
import java.util.SplittableRandom;

/**
 * Tong Ladder (contest gap G339): the tool wall keeps tongs hung by jaw width. Smiths hang, swap and take tongs, and
 * ask for the snuggest tong at least or at most a given width.
 *
 * <p>The tool is plain: an array-backed skip list ordered map from {@code long} to {@code long}, with seeded coin-flip
 * levels (at most {@link #MAX_LEVEL}), giving expected O(log n) put, get, remove, floorKey and ceilingKey. Removed
 * slots are recycled. Any project can use it as a small ordered map without boxing.
 */
public final class TongLadder {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_tong_ladder";

    /** Most levels a node can have. */
    public static final int MAX_LEVEL = 32;

    private static final int NIL = -1;

    /** How a lookup went. */
    public enum Grade { HUNG, DROPPED }

    private long[] keys = new long[16];
    private long[] vals = new long[16];
    private int[][] next = new int[16][];
    private int[] free = new int[16];
    private int freeCount;
    private int used = 1;
    private int level = 1;
    private int size;
    private final SplittableRandom rng;

    /** An empty wall; same seed, same ladder shapes. */
    public TongLadder(long seed) {
        this.rng = new SplittableRandom(seed);
        next[0] = new int[MAX_LEVEL];
        Arrays.fill(next[0], NIL);
    }

    /** Number of tongs on the wall. */
    public int size() {
        return size;
    }

    private int randomLevel() {
        int l = 1;
        while (l < MAX_LEVEL && rng.nextBoolean()) {
            l++;
        }
        return l;
    }

    private int alloc(long k, long v, int lvl) {
        int n;
        if (freeCount > 0) {
            n = free[--freeCount];
        } else {
            if (used == keys.length) {
                int cap = used * 2;
                keys = Arrays.copyOf(keys, cap);
                vals = Arrays.copyOf(vals, cap);
                next = Arrays.copyOf(next, cap);
                free = Arrays.copyOf(free, cap);
            }
            n = used++;
        }
        keys[n] = k;
        vals[n] = v;
        next[n] = new int[lvl];
        Arrays.fill(next[n], NIL);
        return n;
    }

    /** Fill update[i] with the last node before k at level i; return the node at level 0 after it. */
    private int search(long k, int[] update) {
        int x = 0;
        for (int i = level - 1; i >= 0; i--) {
            while (next[x][i] != NIL && keys[next[x][i]] < k) {
                x = next[x][i];
            }
            if (update != null) {
                update[i] = x;
            }
        }
        return next[x][0];
    }

    /** Hang (or re-hang) a tong of width k with tag v. */
    public void put(long k, long v) {
        int[] update = new int[MAX_LEVEL];
        int x = search(k, update);
        if (x != NIL && keys[x] == k) {
            vals[x] = v;
            return;
        }
        int lvl = randomLevel();
        for (int i = level; i < lvl; i++) {
            update[i] = 0;
        }
        level = Math.max(level, lvl);
        int n = alloc(k, v, lvl);
        for (int i = 0; i < lvl; i++) {
            next[n][i] = next[update[i]][i];
            next[update[i]][i] = n;
        }
        size++;
    }

    /** Tag of the tong of width k, if hung. */
    public OptionalLong get(long k) {
        int x = search(k, null);
        return x != NIL && keys[x] == k ? OptionalLong.of(vals[x]) : OptionalLong.empty();
    }

    /** Take the tong of width k; false if none. */
    public boolean remove(long k) {
        int[] update = new int[MAX_LEVEL];
        int x = search(k, update);
        if (x == NIL || keys[x] != k) {
            return false;
        }
        for (int i = 0; i < next[x].length; i++) {
            next[update[i]][i] = next[x][i];
        }
        while (level > 1 && next[0][level - 1] == NIL) {
            level--;
        }
        free[freeCount++] = x;
        size--;
        return true;
    }

    /** Smallest width >= k. */
    public OptionalLong ceilingKey(long k) {
        int x = search(k, null);
        return x == NIL ? OptionalLong.empty() : OptionalLong.of(keys[x]);
    }

    /** Largest width <= k. */
    public OptionalLong floorKey(long k) {
        int x = 0;
        for (int i = level - 1; i >= 0; i--) {
            while (next[x][i] != NIL && keys[next[x][i]] <= k) {
                x = next[x][i];
            }
        }
        return x == 0 ? OptionalLong.empty() : OptionalLong.of(keys[x]);
    }

    /** A seeded script of {@code n} widths in [1, maxWidth]; negative entries mean take that width. */
    public static long[] script(long seed, int n, int maxWidth) {
        if (n < 0 || maxWidth < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxWidth >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] s = new long[n];
        for (int i = 0; i < n; i++) {
            long w = 1 + r.nextInt(maxWidth);
            s[i] = r.nextInt(3) == 0 ? -w : w;
        }
        return s;
    }

    /** HUNG only if the claimed snug fit (ceiling of k) is right. */
    public Grade grade(long k, OptionalLong claimed) {
        return ceilingKey(k).equals(claimed) ? Grade.HUNG : Grade.DROPPED;
    }

    /** The Forgemaster's line for a lookup. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case HUNG -> "Forgemaster: straight to the right peg. Those tongs will grip true.";
            case DROPPED -> "Forgemaster: wrong peg, and the work slips. Read the wall again.";
        };
    }
}
