// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * Lychrel Ladles: ladle n is poured into its own mirror, n -&gt; n + reverse(n), until the melt reads the same both
 * ways (89 needs 24 pours). Ladles that never settle within the pour limit are Lychrel candidates: 196, 295, 394,
 * 493, ... Palindromes settle at zero pours.
 *
 * <p>Reusable API with exact BigInteger digits: {@link #pours}, {@link #melt}, {@link #isLychrelCandidate},
 * {@link #candidatesUpTo} and {@link #seed} (smallest start whose thread passes through n).
 */
public final class LychrelLadles {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_lychrel_ladles";
    /** Largest supported starting ladle. */
    public static final long MAX_N = Long.MAX_VALUE;
    /** Default pour limit. */
    public static final int DEFAULT_LIMIT = 500;
    /** Largest pour limit. */
    public static final int MAX_LIMIT = 5_000;
    /** Largest bound for {@link #candidatesUpTo} and {@link #seed}. */
    public static final int SCAN_MAX = 200_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private LychrelLadles() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("ladle out of range: " + n);
        }
    }

    private static void checkLimit(int limit) {
        if (limit < 0 || limit > MAX_LIMIT) {
            throw new IllegalArgumentException("pour limit out of range: " + limit);
        }
    }

    private static BigInteger mirror(BigInteger v) {
        return new BigInteger(new StringBuilder(v.toString()).reverse().toString());
    }

    private static boolean palindrome(BigInteger v) {
        String s = v.toString();
        for (int i = 0, j = s.length() - 1; i < j; i++, j--) {
            if (s.charAt(i) != s.charAt(j)) {
                return false;
            }
        }
        return true;
    }

    /** Pours needed to reach a palindrome (0 for a palindrome), or -1 when none within the limit. */
    public static int pours(long n, int limit) {
        check(n);
        checkLimit(limit);
        BigInteger v = BigInteger.valueOf(n);
        for (int k = 0; k <= limit; k++) {
            if (palindrome(v)) {
                return k;
            }
            if (k == limit) {
                break;
            }
            v = v.add(mirror(v));
        }
        return -1;
    }

    /** {@link #pours} with {@link #DEFAULT_LIMIT}. */
    public static int pours(long n) {
        return pours(n, DEFAULT_LIMIT);
    }

    /** The melt after k pours. */
    public static BigInteger melt(long n, int k) {
        check(n);
        checkLimit(k);
        BigInteger v = BigInteger.valueOf(n);
        for (int i = 0; i < k; i++) {
            v = v.add(mirror(v));
        }
        return v;
    }

    /** True when n does not reach a palindrome within {@link #DEFAULT_LIMIT} pours. */
    public static boolean isLychrelCandidate(long n) {
        return pours(n) < 0;
    }

    /** Lychrel candidates in 1..x. */
    public static List<Long> candidatesUpTo(int x) {
        if (x < 0 || x > SCAN_MAX) {
            throw new IllegalArgumentException("bound out of range: " + x);
        }
        List<Long> out = new ArrayList<>();
        for (long n = 1; n <= x; n++) {
            if (isLychrelCandidate(n)) {
                out.add(n);
            }
        }
        return out;
    }

    private static long mirrorLong(long v) {
        long r = 0;
        long x = v;
        while (x > 0) {
            r = r * 10 + x % 10;
            x /= 10;
        }
        return r;
    }

    /** Smallest m &lt;= n whose reverse-and-add thread (before settling) passes through n. */
    public static long seed(int n) {
        if (n < 1 || n > SCAN_MAX) {
            throw new IllegalArgumentException("ladle out of range: " + n);
        }
        for (long m = 1; m < n; m++) {
            long v = m;
            while (v < n && mirrorLong(v) != v) {
                v += mirrorLong(v);
            }
            if (v == n) {
                return m;
            }
        }
        return n;
    }

    /** Grade a claim that n is (or is not) a Lychrel candidate. */
    public static Grade grade(long n, boolean claimedLychrel) {
        return isLychrelCandidate(n) == claimedLychrel ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you read the melt right. Some ladles settle, some pour forever.";
            case SLIPPED -> "Forgemaster: the melt slipped. Pour it into its mirror and look again.";
        };
    }
}
