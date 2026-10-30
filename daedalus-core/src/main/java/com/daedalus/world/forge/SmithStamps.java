// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Smith Stamps: a composite stamp n bears the smith's mark when its digit sum equals the total digit sum of its prime
 * factors counted with multiplicity (a Smith number, e.g. 22 = 2 x 11: 2+2 = 2+1+1). The smith checks stamps and
 * counts marked stamps on a rack 1..N with a smallest-prime-factor sieve.
 *
 * <p>Reusable plain long API: {@link #digitSum}, {@link #factorDigitSum}, {@link #isSmith} for 1 &lt;= n &lt;=
 * {@link #MAX_N}, and {@link #countSmith} for N &lt;= {@link #MAX_SIEVE}.
 */
public final class SmithStamps {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_smith_stamps";
    /** Largest supported single stamp. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest supported rack for counting. */
    public static final int MAX_SIEVE = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private SmithStamps() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("stamp out of range: " + n);
        }
    }

    /** Base-10 digit sum of n &gt;= 0. */
    public static int digitSum(long n) {
        if (n < 0) {
            throw new IllegalArgumentException("negative stamp: " + n);
        }
        int s = 0;
        for (long m = n; m > 0; m /= 10) {
            s += (int) (m % 10);
        }
        return s;
    }

    /** Sum of digit sums of the prime factors of n, with multiplicity (0 for n = 1). */
    public static int factorDigitSum(long n) {
        check(n);
        long m = n;
        int s = 0;
        for (long p = 2; p * p <= m; p++) {
            while (m % p == 0) {
                s += digitSum(p);
                m /= p;
            }
        }
        if (m > 1) {
            s += digitSum(m);
        }
        return s;
    }

    static boolean isPrime(long n) {
        if (n < 2) {
            return false;
        }
        for (long f = 2; f * f <= n; f++) {
            if (n % f == 0) {
                return false;
            }
        }
        return true;
    }

    /** True when n is a composite Smith number. */
    public static boolean isSmith(long n) {
        check(n);
        return n > 3 && !isPrime(n) && digitSum(n) == factorDigitSum(n);
    }

    /** Number of Smith numbers in 1..N. */
    public static long countSmith(int bigN) {
        if (bigN < 0 || bigN > MAX_SIEVE) {
            throw new IllegalArgumentException("rack out of range: " + bigN);
        }
        int[] spf = new int[bigN + 1];
        int[] fds = new int[bigN + 1];
        int[] ds = new int[bigN + 1];
        long count = 0;
        for (int i = 1; i <= bigN; i++) {
            ds[i] = ds[i / 10] + i % 10;
        }
        for (int i = 2; i <= bigN; i++) {
            if (spf[i] == 0) {
                for (long j = i; j <= bigN; j += i) {
                    if (spf[(int) j] == 0) {
                        spf[(int) j] = i;
                    }
                }
            }
            int p = spf[i];
            fds[i] = fds[i / p] + ds[p];
            if (p != i && fds[i] == ds[i]) {
                count++;
            }
        }
        return count;
    }

    /** Grade a claim that stamp n is (or is not) a Smith number. */
    public static Grade grade(long n, boolean claimedSmith) {
        return isSmith(n) == claimedSmith ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the stamp's digits match its factors' digits. A true smith's mark.";
            case SLIPPED -> "Forgemaster: the mark slipped. Primes carry no mark; count repeated factors too.";
        };
    }
}
