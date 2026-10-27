// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Untouched Brands: brand n is untouched when no ingot m has aliquot sum s(m) = sigma(m) - m equal to n (an
 * untouchable number: 2, 5, 52, 88, 96, ...).
 *
 * <p>Reusable plain long API: {@link #aliquotSum} for 1 &lt;= m &lt;= {@link #MAX_M}; {@link #witness},
 * {@link #isUntouched} and {@link #untouchedUpTo} for brands up to {@link #MAX_BRAND}. A composite m has
 * s(m) &gt; sqrt(m) and a prime has s(m) = 1, so only m &lt; N^2 can touch a brand n &lt;= N; those are sieved once.
 */
public final class UntouchedBrands {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_untouched_brands";
    /** Largest supported ingot for {@link #aliquotSum}. */
    public static final long MAX_M = 1_000_000_000_000L;
    /** Largest supported brand. */
    public static final int MAX_BRAND = 3000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private static int[] witnesses;

    private UntouchedBrands() {
    }

    /** Aliquot sum s(m) = sum of the proper divisors of m (0 for m = 1). */
    public static long aliquotSum(long m) {
        if (m < 1 || m > MAX_M) {
            throw new IllegalArgumentException("ingot out of range: " + m);
        }
        if (m == 1) {
            return 0;
        }
        long s = 1;
        for (long d = 2; d * d <= m; d++) {
            if (m % d == 0) {
                s += d;
                if (d != m / d) {
                    s += m / d;
                }
            }
        }
        return s;
    }

    private static synchronized int[] table() {
        if (witnesses == null) {
            int n = MAX_BRAND;
            int lim = n * n;
            int[] sig = new int[lim + 1];
            for (int d = 1; d <= lim / 2; d++) {
                for (int k = 2 * d; k <= lim; k += d) {
                    sig[k] += d;
                }
            }
            int[] w = new int[n + 1];
            for (int m = 1; m <= lim; m++) {
                int s = sig[m];
                if (s >= 1 && s <= n && w[s] == 0) {
                    w[s] = m;
                }
            }
            witnesses = w;
        }
        return witnesses;
    }

    private static void checkBrand(long n) {
        if (n < 1 || n > MAX_BRAND) {
            throw new IllegalArgumentException("brand out of range: " + n);
        }
    }

    /** Smallest ingot m with s(m) = n, or -1 when brand n is untouched. */
    public static long witness(long n) {
        checkBrand(n);
        int w = table()[(int) n];
        return w == 0 ? -1 : w;
    }

    /** True when no ingot has aliquot sum n. */
    public static boolean isUntouched(long n) {
        return witness(n) < 0;
    }

    /** All untouched brands in 1..limit (limit between 0 and {@link #MAX_BRAND}). */
    public static List<Long> untouchedUpTo(int limit) {
        if (limit < 0 || limit > MAX_BRAND) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<Long> out = new ArrayList<>();
        for (long n = 1; n <= limit; n++) {
            if (isUntouched(n)) {
                out.add(n);
            }
        }
        return out;
    }

    /** Grade a claim that brand n is (or is not) untouched. */
    public static Grade grade(long n, boolean claimedUntouched) {
        return isUntouched(n) == claimedUntouched ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you read the brand true. No ingot's lesser parts sum to it, or one does.";
            case SLIPPED -> "Forgemaster: the brand slipped. Sum an ingot's proper divisors and look again.";
        };
    }
}
