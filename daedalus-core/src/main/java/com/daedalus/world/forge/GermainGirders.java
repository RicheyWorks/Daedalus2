// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Germain Girders: girder p is a Sophie Germain girder when p and 2p + 1 are both prime; 2p + 1 is then a safe
 * girder. Welding p -&gt; 2p + 1 while the result stays prime gives a Cunningham chain of the first kind
 * (2, 5, 11, 23, 47 and 89, 179, 359, 719, 1439, 2879).
 *
 * <p>Reusable plain long API for 1 &lt;= p &lt;= {@link #MAX_N} with primality from
 * {@link PrimorialPyres#isPrime}: {@link #isGermain}, {@link #isSafe}, {@link #chainLength} and the sieve
 * {@link #countGermain} for x up to {@link #SIEVE_MAX}.
 */
public final class GermainGirders {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_germain_girders";
    /** Largest supported girder. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;
    /** Largest sieve bound for {@link #countGermain}. */
    public static final int SIEVE_MAX = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private GermainGirders() {
    }

    private static void check(long p) {
        if (p < 1 || p > MAX_N) {
            throw new IllegalArgumentException("girder out of range: " + p);
        }
    }

    /** True when p and 2p + 1 are prime. */
    public static boolean isGermain(long p) {
        check(p);
        return PrimorialPyres.isPrime(p) && PrimorialPyres.isPrime(2 * p + 1);
    }

    /** True when q and (q - 1) / 2 are prime. */
    public static boolean isSafe(long q) {
        check(q);
        return (q & 1) != 0 && q > 3 && PrimorialPyres.isPrime(q) && PrimorialPyres.isPrime((q - 1) / 2);
    }

    /** Number of primes in p, 2p + 1, 4p + 3, ... before the first composite (0 when p is not prime). */
    public static int chainLength(long p) {
        check(p);
        int len = 0;
        long v = p;
        while (PrimorialPyres.isPrime(v)) {
            len++;
            if (v > (Long.MAX_VALUE - 1) / 2) {
                break;
            }
            v = 2 * v + 1;
        }
        return len;
    }

    /** Number of Sophie Germain primes p &lt;= x, by sieve. */
    public static int countGermain(int x) {
        if (x < 0 || x > SIEVE_MAX) {
            throw new IllegalArgumentException("bound out of range: " + x);
        }
        int top = 2 * x + 1;
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
        int c = 0;
        for (int p = 2; p <= x; p++) {
            if (!comp[p] && !comp[2 * p + 1]) {
                c++;
            }
        }
        return c;
    }

    /** Grade a claim that p is (or is not) a Sophie Germain girder. */
    public static Grade grade(long p, boolean claimedGermain) {
        return isGermain(p) == claimedGermain ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the girder holds, and its double-plus-one holds too.";
            case SLIPPED -> "Forgemaster: the weld cracked. Check p and 2p + 1 both.";
        };
    }
}
