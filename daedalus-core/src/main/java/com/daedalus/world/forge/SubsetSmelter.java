// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Subset Smelter: n ore types, every alloy is a subset (bitmask) of them. The smith totals yield over all sub-alloys
 * (zeta transform), recovers single-alloy yields from totals (Moebius transform), and fuses two disjoint alloys
 * optimally counted by subset convolution, all in O(2^n n^2) instead of O(3^n) or O(4^n).
 *
 * <p>Reusable plain long API (exact, wrapping on overflow like Java long): {@link #zeta}, {@link #mobius},
 * {@link #supersetZeta} and {@link #subsetConvolution} for 0 &lt;= n &lt;= {@link #MAX_BITS}.
 */
public final class SubsetSmelter {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_subset_smelter";
    /** Largest supported number of ore types. */
    public static final int MAX_BITS = 20;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private SubsetSmelter() {
    }

    private static int bits(long[] f) {
        if (f == null) {
            throw new IllegalArgumentException("null table");
        }
        int n = Integer.numberOfTrailingZeros(f.length);
        if (f.length == 0 || Integer.bitCount(f.length) != 1 || n > MAX_BITS) {
            throw new IllegalArgumentException("table length must be 2^n with n <= " + MAX_BITS);
        }
        return n;
    }

    /** g[S] = sum of f[T] over subsets T of S. */
    public static long[] zeta(long[] f) {
        int n = bits(f);
        long[] g = f.clone();
        for (int i = 0; i < n; i++) {
            for (int s = 0; s < g.length; s++) {
                if ((s >> i & 1) == 1) {
                    g[s] += g[s ^ (1 << i)];
                }
            }
        }
        return g;
    }

    /** Inverse of {@link #zeta}: f[S] = sum over subsets T of S of (-1)^|S\T| g[T]. */
    public static long[] mobius(long[] g) {
        int n = bits(g);
        long[] f = g.clone();
        for (int i = 0; i < n; i++) {
            for (int s = 0; s < f.length; s++) {
                if ((s >> i & 1) == 1) {
                    f[s] -= f[s ^ (1 << i)];
                }
            }
        }
        return f;
    }

    /** g[S] = sum of f[T] over supersets T of S. */
    public static long[] supersetZeta(long[] f) {
        int n = bits(f);
        long[] g = f.clone();
        for (int i = 0; i < n; i++) {
            for (int s = 0; s < g.length; s++) {
                if ((s >> i & 1) == 0) {
                    g[s] += g[s | (1 << i)];
                }
            }
        }
        return g;
    }

    /** h[S] = sum over T subset S of a[T] * b[S \ T] (ranked zeta transform). */
    public static long[] subsetConvolution(long[] a, long[] b) {
        int n = bits(a);
        if (b == null || b.length != a.length) {
            throw new IllegalArgumentException("tables must match");
        }
        int size = a.length;
        long[][] fa = new long[n + 1][size];
        long[][] fb = new long[n + 1][size];
        for (int s = 0; s < size; s++) {
            fa[Integer.bitCount(s)][s] = a[s];
            fb[Integer.bitCount(s)][s] = b[s];
        }
        for (int k = 0; k <= n; k++) {
            fa[k] = zeta(fa[k]);
            fb[k] = zeta(fb[k]);
        }
        long[] h = new long[size];
        for (int k = 0; k <= n; k++) {
            long[] hk = new long[size];
            for (int j = 0; j <= k; j++) {
                long[] x = fa[j];
                long[] y = fb[k - j];
                for (int s = 0; s < size; s++) {
                    hk[s] += x[s] * y[s];
                }
            }
            hk = mobius(hk);
            for (int s = 0; s < size; s++) {
                if (Integer.bitCount(s) == k) {
                    h[s] = hk[s];
                }
            }
        }
        return h;
    }

    /** Grade a claimed zeta total for alloy mask s. */
    public static Grade grade(long[] f, int s, long claimed) {
        long[] g = zeta(f);
        return s >= 0 && s < g.length && g[s] == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every sub-alloy weighed once, one ore at a time. True smelt.";
            case SLIPPED -> "Forgemaster: the smelt slipped. Fold in one ore bit per pass, not all subsets at once.";
        };
    }
}
