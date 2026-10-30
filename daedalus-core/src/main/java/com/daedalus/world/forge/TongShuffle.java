// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Tong Shuffle (contest gap G259): an apprentice hangs a rack of tongs out of order. Say how many adjacent swaps put it
 * right, and which numbered arrangement it is in the guild's catalogue.
 *
 * <p>The tool is plain: {@link #inversions} is an O(n log n) merge-sort inversion count on any {@code int[]}, and
 * {@link #rank} / {@link #unrank} map a permutation of 0..n-1 (n at most {@link #MAX_RANK_N}) to and from its
 * lexicographic index via the Lehmer code and a Fenwick tree. Any project can use it for sortedness metrics or
 * permutation indexing.
 */
public final class TongShuffle {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_tong_shuffle";

    /** Largest n whose n! fits in a long. */
    public static final int MAX_RANK_N = 20;

    /** How an answer went. */
    public enum Grade { TIDY, TANGLED }

    private TongShuffle() {
    }

    /** A seeded shuffle of tongs 0..n-1 (Fisher-Yates). Same seed, same rack. */
    public static int[] rack(long seed, int n) {
        if (n < 0) {
            throw new IllegalArgumentException("need n >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = i;
        }
        for (int i = n - 1; i > 0; i--) {
            int j = r.nextInt(i + 1);
            int t = p[i];
            p[i] = p[j];
            p[j] = t;
        }
        return p;
    }

    /** Number of pairs i < j with a[i] > a[j] (= fewest adjacent swaps to sort). */
    public static long inversions(int[] a) {
        int[] buf = a.clone();
        return sortCount(buf, new int[a.length], 0, a.length);
    }

    private static long sortCount(int[] a, int[] tmp, int lo, int hi) {
        if (hi - lo < 2) {
            return 0;
        }
        int mid = (lo + hi) >>> 1;
        long c = sortCount(a, tmp, lo, mid) + sortCount(a, tmp, mid, hi);
        int i = lo;
        int j = mid;
        int k = lo;
        while (i < mid && j < hi) {
            if (a[j] < a[i]) {
                c += mid - i;
                tmp[k++] = a[j++];
            } else {
                tmp[k++] = a[i++];
            }
        }
        while (i < mid) {
            tmp[k++] = a[i++];
        }
        while (j < hi) {
            tmp[k++] = a[j++];
        }
        System.arraycopy(tmp, lo, a, lo, hi - lo);
        return c;
    }

    private static void checkN(int n) {
        if (n < 0 || n > MAX_RANK_N) {
            throw new IllegalArgumentException("need 0 <= n <= " + MAX_RANK_N);
        }
    }

    private static long factorial(int n) {
        long f = 1;
        for (int i = 2; i <= n; i++) {
            f *= i;
        }
        return f;
    }

    /** Lexicographic index (0-based) of a permutation of 0..n-1. */
    public static long rank(int[] p) {
        int n = p.length;
        checkN(n);
        int[] tree = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            tree[i] += 1;
            int up = i + (i & -i);
            if (up <= n) {
                tree[up] += tree[i];
            }
        }
        boolean[] seen = new boolean[n];
        long r = 0;
        for (int i = 0; i < n; i++) {
            int v = p[i];
            if (v < 0 || v >= n || seen[v]) {
                throw new IllegalArgumentException("not a permutation of 0.." + (n - 1));
            }
            seen[v] = true;
            int smaller = 0;
            for (int x = v; x > 0; x -= x & -x) {
                smaller += tree[x];
            }
            r += smaller * factorial(n - 1 - i);
            for (int x = v + 1; x <= n; x += x & -x) {
                tree[x]--;
            }
        }
        return r;
    }

    /** The permutation of 0..n-1 at lexicographic index {@code r}. */
    public static int[] unrank(int n, long r) {
        checkN(n);
        if (r < 0 || r >= factorial(n)) {
            throw new IllegalArgumentException("rank out of range");
        }
        int[] tree = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            tree[i] += 1;
            int up = i + (i & -i);
            if (up <= n) {
                tree[up] += tree[i];
            }
        }
        int log = 1;
        while ((1 << log) <= n) {
            log++;
        }
        int[] p = new int[n];
        long rem = r;
        for (int i = 0; i < n; i++) {
            long f = factorial(n - 1 - i);
            int k = (int) (rem / f);
            rem %= f;
            int pos = 0;
            int left = k;
            for (int b = 1 << log; b > 0; b >>= 1) {
                if (pos + b <= n && tree[pos + b] <= left) {
                    pos += b;
                    left -= tree[pos];
                }
            }
            p[i] = pos;
            for (int x = pos + 1; x <= n; x += x & -x) {
                tree[x]--;
            }
        }
        return p;
    }

    /** TIDY only if both the swap count and the catalogue number are right. */
    public static Grade grade(int[] p, long swaps, long catalogue) {
        return inversions(p) == swaps && rank(p) == catalogue ? Grade.TIDY : Grade.TANGLED;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TIDY -> "Forgemaster: every tong on its hook, and you knew the catalogue number cold.";
            case TANGLED -> "Forgemaster: the rack is still a tangle. Count the crossings again.";
        };
    }
}
