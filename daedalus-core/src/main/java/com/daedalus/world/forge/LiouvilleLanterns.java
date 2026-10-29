// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Liouville Lanterns: lantern n burns bright when n has an even number of prime factors counted with multiplicity
 * and dark when odd (the Liouville function lambda(n) = (-1)^Omega(n)). The smith names a lantern's shade, its
 * factor counts, and the running balance L(N) = sum of lambda(n) for n &lt;= N along the forge wall.
 *
 * <p>Reusable plain long API: {@link #bigOmega}, {@link #littleOmega}, {@link #lambda} for 1 &lt;= n &lt;=
 * {@link #MAX_N}, and {@link #summatory} via a smallest-prime-factor sieve for N &lt;= {@link #MAX_SIEVE}.
 */
public final class LiouvilleLanterns {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_liouville_lanterns";
    /** Largest supported single lantern. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest supported wall length for the running balance. */
    public static final int MAX_SIEVE = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private LiouvilleLanterns() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("lantern out of range: " + n);
        }
    }

    private static int[] counts(long n) {
        check(n);
        long m = n;
        int big = 0;
        int little = 0;
        for (long p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                little++;
                while (m % p == 0) {
                    m /= p;
                    big++;
                }
            }
        }
        if (m > 1) {
            little++;
            big++;
        }
        return new int[] {big, little};
    }

    /** Number of prime factors of n counted with multiplicity. */
    public static int bigOmega(long n) {
        return counts(n)[0];
    }

    /** Number of distinct prime factors of n. */
    public static int littleOmega(long n) {
        return counts(n)[1];
    }

    /** Liouville lambda(n) = (-1)^Omega(n). */
    public static int lambda(long n) {
        return (bigOmega(n) & 1) == 0 ? 1 : -1;
    }

    /** Running balance L(N) = sum_{n=1..N} lambda(n); L(0) = 0. */
    public static long summatory(int bigN) {
        if (bigN < 0 || bigN > MAX_SIEVE) {
            throw new IllegalArgumentException("wall out of range: " + bigN);
        }
        if (bigN == 0) {
            return 0;
        }
        int[] spf = new int[bigN + 1];
        byte[] par = new byte[bigN + 1];
        long sum = 1;
        for (int i = 2; i <= bigN; i++) {
            if (spf[i] == 0) {
                for (long j = i; j <= bigN; j += i) {
                    if (spf[(int) j] == 0) {
                        spf[(int) j] = i;
                    }
                }
            }
            par[i] = (byte) (par[i / spf[i]] ^ 1);
            sum += par[i] == 0 ? 1 : -1;
        }
        return sum;
    }

    /** Grade a claimed shade (+1 bright, -1 dark) for lantern n. */
    public static Grade grade(long n, int claimed) {
        return lambda(n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: counted every prime, repeats and all. The lantern shows true.";
            case SLIPPED -> "Forgemaster: wrong shade. Count the repeated primes too; parity decides the flame.";
        };
    }
}
