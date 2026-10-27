// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G313 The Clean Lots: a cargo lot number is clean when no square above 1 divides it (squarefree).
 * A linear sieve gives the Mobius function mu; clean lots up to N are counted as the sum of
 * mu(d) * floor(N / d^2) for d up to sqrt(N), Mertens sums add mu, and pairs of mooring posts
 * (a, b) in 1..N with gcd 1 are counted by Mobius inversion.
 */
public final class CleanLots {

    public static final String QUEST_ID = "q_clean_lots";
    public static final int MAX_SIEVE = 20_000_000;

    private CleanLots() { }

    /** mu[0..limit-1] by a linear sieve (mu[0] = 0). */
    public static int[] mobius(int limit) {
        if (limit < 2 || limit > MAX_SIEVE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        int[] mu = new int[limit];
        int[] primes = new int[limit];
        boolean[] composite = new boolean[limit];
        int count = 0;
        mu[1] = 1;
        for (int i = 2; i < limit; i++) {
            if (!composite[i]) {
                primes[count++] = i;
                mu[i] = -1;
            }
            for (int j = 0; j < count && (long) i * primes[j] < limit; j++) {
                int v = i * primes[j];
                composite[v] = true;
                if (i % primes[j] == 0) {
                    mu[v] = 0;
                    break;
                }
                mu[v] = -mu[i];
            }
        }
        return mu;
    }

    /** Clean (squarefree) lots in 1..n, for 0 <= n <= 10^14. */
    public static long cleanCount(long n) {
        if (n < 0 || n > 100_000_000_000_000L) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        if (n == 0) {
            return 0;
        }
        int root = (int) SquareHatches.isqrt(n);
        int[] mu = mobius(root + 2);
        long total = 0;
        for (long d = 1; d <= root; d++) {
            total += mu[(int) d] * (n / (d * d));
        }
        return total;
    }

    /** Mertens M(n) = mu(1) + ... + mu(n). */
    public static long mertens(int n) {
        int[] mu = mobius(Math.max(n + 1, 2));
        long s = 0;
        for (int i = 1; i <= n; i++) {
            s += mu[i];
        }
        return s;
    }

    /** Ordered pairs (a, b) in 1..n x 1..n with gcd(a, b) = 1. */
    public static long coprimePairs(int n) {
        int[] mu = mobius(Math.max(n + 1, 2));
        long s = 0;
        for (int d = 1; d <= n; d++) {
            long q = n / d;
            s += mu[d] * q * q;
        }
        return s;
    }

    /** Quest q_clean_lots: the purser names how many clean lots lie in 1..n. */
    public static boolean quest(long n, long answer) {
        return cleanCount(n) == answer;
    }
}