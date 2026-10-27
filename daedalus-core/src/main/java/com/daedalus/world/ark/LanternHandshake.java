// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G271 The Lantern Handshake: two arks agree a shared lantern code across open sky without ever
 * flashing it. Each picks a secret, flashes {@code g^secret mod p}, and raises the other's flash
 * to its own secret (a toy Diffie-Hellman; game-only, NOT real cryptography). {@link #power} is
 * square-and-multiply and counts its multiplications; {@link #isPrime} is Miller-Rabin with bases
 * 2, 3, 5, 7, which is exact below 3,215,031,751. Moduli stay below {@link #MAX_MOD} so every
 * product fits in a long.
 */
public final class LanternHandshake {

    public static final String QUEST_ID = "q_lantern_handshake";
    /** floor(sqrt(Long.MAX_VALUE)): products of residues below this fit in a long. */
    public static final long MAX_MOD = 3_037_000_499L;

    /** {@code base^exp mod m} and how many modular multiplications it took. */
    public record Power(long value, int multiplications) { }

    /** What each ark flashes and the code both end up with. */
    public record Handshake(long flashA, long flashB, long code) { }

    private LanternHandshake() { }

    public static Power power(long base, long exp, long m) {
        if (m < 1 || m > MAX_MOD || exp < 0 || base < 0) {
            throw new IllegalArgumentException("bad base, exponent or modulus");
        }
        long result = 1 % m;
        long b = base % m;
        int mults = 0;
        for (long e = exp; e > 0; e >>>= 1) {
            if ((e & 1) != 0) {
                result = result * b % m;
                mults++;
            }
            if (e > 1) {
                b = b * b % m;
                mults++;
            }
        }
        return new Power(result, mults);
    }

    public static long powMod(long base, long exp, long m) {
        return power(base, exp, m).value();
    }

    /** Deterministic Miller-Rabin for 0 &lt;= n &lt; MAX_MOD. */
    public static boolean isPrime(long n) {
        if (n < 0 || n >= MAX_MOD) {
            throw new IllegalArgumentException("n out of range");
        }
        if (n < 2) {
            return false;
        }
        for (long p : new long[] {2, 3, 5, 7}) {
            if (n % p == 0) {
                return n == p;
            }
        }
        long d = n - 1;
        int s = 0;
        while ((d & 1) == 0) {
            d >>= 1;
            s++;
        }
        for (long a : new long[] {2, 3, 5, 7}) {
            long x = powMod(a, d, n);
            if (x == 1 || x == n - 1) {
                continue;
            }
            boolean witness = true;
            for (int r = 1; r < s; r++) {
                x = x * x % n;
                if (x == n - 1) {
                    witness = false;
                    break;
                }
            }
            if (witness) {
                return false;
            }
        }
        return true;
    }

    /** Plays the handshake; p must be prime and 1 &lt; g &lt; p. */
    public static Handshake handshake(long p, long g, long secretA, long secretB) {
        if (!isPrime(p) || g <= 1 || g >= p || secretA < 1 || secretB < 1) {
            throw new IllegalArgumentException("bad handshake");
        }
        long fa = powMod(g, secretA, p);
        long fb = powMod(g, secretB, p);
        long code = powMod(fb, secretA, p);
        return new Handshake(fa, fb, code);
    }

    /** Quest q_lantern_handshake: from ark A's seat, name the shared code. */
    public static boolean quest(long p, long g, long secretA, long secretB, long answer) {
        return handshake(p, g, secretA, secretB).code() == answer;
    }
}
