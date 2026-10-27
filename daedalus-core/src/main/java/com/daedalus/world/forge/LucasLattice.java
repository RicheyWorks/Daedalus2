// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Lucas Lattice: the forge lattice stacks Pascal's triangle in rows of up to 10^18 rivets. The smith names how many
 * ways k rivets fit in row n modulo a prime p (Lucas's theorem) and how many times p divides that count (Kummer's
 * carry count).
 *
 * <p>Reusable plain long API: {@link #binomialMod} and {@link #primeExponent} for 0 &lt;= k, n &lt;= 10^18 and primes
 * p &lt;= {@link #MAX_P}.
 */
public final class LucasLattice {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_lucas_lattice";
    /** Largest supported prime modulus. */
    public static final int MAX_P = 1_000_003;
    /** Largest supported row. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private LucasLattice() {
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

    private static void check(long n, long k, long p) {
        if (n < 0 || n > MAX_N || k < 0 || p > MAX_P || !isPrime(p)) {
            throw new IllegalArgumentException("bad lattice query n=" + n + " k=" + k + " p=" + p);
        }
    }

    private static long powMod(long b, long e, long m) {
        long r = 1;
        long x = b % m;
        long k = e;
        while (k > 0) {
            if ((k & 1) == 1) {
                r = r * x % m;
            }
            x = x * x % m;
            k >>= 1;
        }
        return r;
    }

    private static long smallBinom(long n, long k, long p) {
        if (k > n) {
            return 0;
        }
        long num = 1;
        long den = 1;
        for (long i = 0; i < k; i++) {
            num = num * ((n - i) % p) % p;
            den = den * ((i + 1) % p) % p;
        }
        return num * powMod(den, p - 2, p) % p;
    }

    /** C(n, k) mod p by Lucas's theorem (0 when k &gt; n). */
    public static long binomialMod(long n, long k, long p) {
        check(n, k, p);
        long r = 1 % p;
        long a = n;
        long b = k;
        while (b > 0 || a > 0) {
            long ad = a % p;
            long bd = b % p;
            if (bd > ad) {
                return 0;
            }
            r = r * smallBinom(ad, Math.min(bd, ad - bd), p) % p;
            a /= p;
            b /= p;
        }
        return r;
    }

    /** Exponent of p in C(n, k): the number of carries adding k and n-k in base p (Kummer); -1 when k &gt; n. */
    public static int primeExponent(long n, long k, long p) {
        check(n, k, p);
        if (k > n) {
            return -1;
        }
        long a = k;
        long b = n - k;
        int carries = 0;
        long carry = 0;
        while (a > 0 || b > 0 || carry > 0) {
            long s = a % p + b % p + carry;
            carry = s >= p ? 1 : 0;
            carries += (int) carry;
            a /= p;
            b /= p;
        }
        return carries;
    }

    /** Grade a claimed residue of C(n, k) mod p. */
    public static Grade grade(long n, long k, long p, long claimed) {
        return binomialMod(n, k, p) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: digit by digit in base p, the lattice holds. Lucas would sign it.";
            case SLIPPED -> "Forgemaster: the lattice slipped. Split n and k into base-p digits and multiply.";
        };
    }
}
