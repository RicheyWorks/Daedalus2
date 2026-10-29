// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Emirp Embers: ember n glows twice when n is prime and its decimal reversal is a different prime (emirps 13, 17,
 * 31, 37, 71, 73, 79, 97, ...). Palindromic primes such as 11 or 101 glow once and do not count.
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N}, primality from {@link PrimorialPyres#isPrime}:
 * {@link #reverse}, {@link #isEmirp} and the sieve {@link #emirpsUpTo} for x up to {@link #SIEVE_MAX}.
 */
public final class EmirpEmbers {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_emirp_embers";
    /** Largest supported ember. */
    public static final long MAX_N = 999_999_999_999_999_999L;
    /** Largest sieve bound. */
    public static final int SIEVE_MAX = 9_999_999;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private EmirpEmbers() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("ember out of range: " + n);
        }
    }

    /** Decimal digit reversal (trailing zeros drop: 120 -&gt; 21). */
    public static long reverse(long n) {
        check(n);
        long r = 0;
        long v = n;
        while (v > 0) {
            r = r * 10 + v % 10;
            v /= 10;
        }
        return r;
    }

    /** True when n and reverse(n) are distinct primes. */
    public static boolean isEmirp(long n) {
        long r = reverse(n);
        return r != n && PrimorialPyres.isPrime(n) && PrimorialPyres.isPrime(r);
    }

    /** Emirps in 1..x, by a sieve over the full digit range of x. */
    public static List<Long> emirpsUpTo(int x) {
        if (x < 0 || x > SIEVE_MAX) {
            throw new IllegalArgumentException("bound out of range: " + x);
        }
        int top = 9;
        while (top < x) {
            top = top * 10 + 9;
        }
        boolean[] comp = new boolean[top + 1];
        comp[0] = true;
        comp[1] = true;
        for (long i = 2; i * i <= top; i++) {
            if (!comp[(int) i]) {
                for (long j = i * i; j <= top; j += i) {
                    comp[(int) j] = true;
                }
            }
        }
        List<Long> out = new ArrayList<>();
        for (int n = 2; n <= x; n++) {
            if (!comp[n]) {
                int r = (int) reverse(n);
                if (r != n && !comp[r]) {
                    out.add((long) n);
                }
            }
        }
        return out;
    }

    /** Grade a claim that n is (or is not) an emirp. */
    public static Grade grade(long n, boolean claimedEmirp) {
        return isEmirp(n) == claimedEmirp ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the ember glows both ways. Read it backward and it still burns prime.";
            case SLIPPED -> "Forgemaster: the ember went dark. Flip its digits and test again.";
        };
    }
}
