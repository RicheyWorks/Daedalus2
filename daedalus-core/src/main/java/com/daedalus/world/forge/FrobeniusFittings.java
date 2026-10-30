// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Frobenius Fittings: the forge sells bolts only in fixed pack sizes. The smith names the largest order that no mix
 * of packs can fill exactly (the Frobenius number), how many orders are impossible, and whether a given order fits.
 *
 * <p>Reusable API: {@link #residueTable} (Boecker-Liptak round-robin shortest paths mod the smallest pack),
 * {@link #frobenius}, {@link #countGaps} and {@link #representable}. Pack sizes are 1..{@link #MAX_PACK} for the
 * smallest pack, at most {@link #MAX_VALUE} for the others, up to {@link #MAX_PACKS} packs.
 */
public final class FrobeniusFittings {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_frobenius_fittings";
    /** Largest supported smallest pack. */
    public static final int MAX_PACK = 200_000;
    /** Largest supported pack size. */
    public static final long MAX_VALUE = 1_000_000_000L;
    /** Largest supported number of packs. */
    public static final int MAX_PACKS = 32;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private FrobeniusFittings() {
    }

    static long gcd(long a, long b) {
        long x = a;
        long y = b;
        while (y != 0) {
            long t = x % y;
            x = y;
            y = t;
        }
        return x;
    }

    private static long[] sorted(long[] packs) {
        if (packs == null || packs.length == 0 || packs.length > MAX_PACKS) {
            throw new IllegalArgumentException("need 1.." + MAX_PACKS + " packs");
        }
        long[] a = packs.clone();
        Arrays.sort(a);
        if (a[0] < 1 || a[0] > MAX_PACK || a[a.length - 1] > MAX_VALUE) {
            throw new IllegalArgumentException("pack size out of range");
        }
        return a;
    }

    /** Smallest representable total in each residue class mod the smallest pack (Long.MAX_VALUE if none). */
    public static long[] residueTable(long[] packs) {
        long[] a = sorted(packs);
        int m = (int) a[0];
        long[] dist = new long[m];
        Arrays.fill(dist, Long.MAX_VALUE);
        dist[0] = 0;
        for (int i = 1; i < a.length; i++) {
            long c = a[i];
            int d = (int) gcd(m, c);
            for (int p = 0; p < d; p++) {
                long n = Long.MAX_VALUE;
                for (int q = p; q < m; q += d) {
                    n = Math.min(n, dist[q]);
                }
                if (n == Long.MAX_VALUE) {
                    continue;
                }
                for (int j = 0; j < m / d; j++) {
                    n += c;
                    int r = (int) (n % m);
                    n = Math.min(n, dist[r]);
                    dist[r] = n;
                }
            }
        }
        return dist;
    }

    /** Largest total no mix can fill; -1 when every total fits, Long.MAX_VALUE when packs share a factor. */
    public static long frobenius(long[] packs) {
        long[] dist = residueTable(packs);
        long mx = 0;
        for (long v : dist) {
            mx = Math.max(mx, v);
        }
        return mx == Long.MAX_VALUE ? Long.MAX_VALUE : mx - dist.length;
    }

    /** Number of positive totals no mix can fill; Long.MAX_VALUE when infinite. */
    public static long countGaps(long[] packs) {
        long[] dist = residueTable(packs);
        long s = 0;
        for (int r = 0; r < dist.length; r++) {
            if (dist[r] == Long.MAX_VALUE) {
                return Long.MAX_VALUE;
            }
            s += (dist[r] - r) / dist.length;
        }
        return s;
    }

    /** True when total n is a nonnegative mix of the packs. */
    public static boolean representable(long[] packs, long n) {
        if (n < 0) {
            return false;
        }
        long[] dist = residueTable(packs);
        return n >= dist[(int) (n % dist.length)];
    }

    /** Grade a claimed Frobenius number. */
    public static Grade grade(long[] packs, long claimed) {
        return frobenius(packs) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: past that order every bolt count fits. The fittings are sound.";
            case SLIPPED -> "Forgemaster: the fitting slipped. Chase the cheapest total in each residue of the "
                + "smallest pack.";
        };
    }
}
