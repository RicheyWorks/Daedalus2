// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G288 The Pascal Sail: the sailmaker stitches Pascal's triangle into a sail and colours each cell
 * by C(n, k) mod a prime p. Lucas' theorem gives C(n, k) mod p for huge n from the base-p digits;
 * Kummer's theorem gives the power of p dividing C(n, k) as the carries in k + (n - k) in base p;
 * row n holds 2^popcount(n) odd cells (the Sierpinski pattern).
 */
public final class PascalSail {

    public static final String QUEST_ID = "q_pascal_sail";
    public static final int MAX_PRIME = 1_000_003;

    private PascalSail() { }

    private static void checkPrime(int p) {
        if (p < 2 || p > MAX_PRIME) {
            throw new IllegalArgumentException("prime out of range: " + p);
        }
        for (int d = 2; (long) d * d <= p; d++) {
            if (p % d == 0) {
                throw new IllegalArgumentException("not a prime: " + p);
            }
        }
    }

    private static long modPow(long b, long e, long m) {
        long r = 1 % m;
        long x = b % m;
        for (long k = e; k > 0; k >>= 1) {
            if ((k & 1) == 1) {
                r = r * x % m;
            }
            x = x * x % m;
        }
        return r;
    }

    /** C(n, k) mod p by Lucas' theorem; 0 when k is outside 0..n. */
    public static int binomMod(long n, long k, int p) {
        checkPrime(p);
        if (n < 0) {
            throw new IllegalArgumentException("n must be >= 0");
        }
        if (k < 0 || k > n) {
            return 0;
        }
        long[] fact = new long[p];
        fact[0] = 1;
        for (int i = 1; i < p; i++) {
            fact[i] = fact[i - 1] * i % p;
        }
        long r = 1;
        long nn = n;
        long kk = k;
        while (kk > 0 || nn > 0) {
            int a = (int) (nn % p);
            int b = (int) (kk % p);
            if (b > a) {
                return 0;
            }
            long den = fact[b] * fact[a - b] % p;
            r = r * fact[a] % p * modPow(den, p - 2L, p) % p;
            nn /= p;
            kk /= p;
        }
        return (int) r;
    }

    /** Exponent of p in C(n, k): carries when adding k and n - k in base p. */
    public static int pPower(long n, long k, int p) {
        checkPrime(p);
        if (n < 0 || k < 0 || k > n) {
            throw new IllegalArgumentException("need 0 <= k <= n");
        }
        long a = k;
        long b = n - k;
        int carry = 0;
        int carries = 0;
        while (a > 0 || b > 0) {
            long s = a % p + b % p + carry;
            carry = s >= p ? 1 : 0;
            carries += carry;
            a /= p;
            b /= p;
        }
        return carries;
    }

    /** Odd cells in sail row n: 2^popcount(n). */
    public static long oddCells(long n) {
        if (n < 0) {
            throw new IllegalArgumentException("n must be >= 0");
        }
        return 1L << Long.bitCount(n);
    }

    /** Quest q_pascal_sail: the sailmaker names the colour C(n, k) mod p of one cell. */
    public static boolean quest(long n, long k, int p, int answer) {
        return binomMod(n, k, p) == answer;
    }
}