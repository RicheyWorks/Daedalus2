// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Ramanujan Rings: q bells hang evenly on a ring; striking the bells coprime to q with stride n leaves a whole-number
 * echo, the Ramanujan sum c_q(n) = sum over gcd(a,q)=1 of cos(2 pi a n / q). The smith names the echo, and the ring's
 * Dedekind psi and Jordan totient counts.
 *
 * <p>Reusable plain long API: {@link #ramanujanSum} (von Sterneck formula mu(q/d) phi(q)/phi(q/d), d = gcd(n,q)),
 * {@link #totient}, {@link #mobius}, {@link #dedekindPsi} and {@link #jordanTotient} for
 * 1 &lt;= q &lt;= {@link #MAX_Q}.
 */
public final class RamanujanRings {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_ramanujan_rings";
    /** Largest supported ring. */
    public static final long MAX_Q = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private RamanujanRings() {
    }

    private static void check(long q) {
        if (q < 1 || q > MAX_Q) {
            throw new IllegalArgumentException("ring out of range: " + q);
        }
    }

    static long gcd(long a, long b) {
        long x = Math.abs(a);
        long y = Math.abs(b);
        while (y != 0) {
            long t = x % y;
            x = y;
            y = t;
        }
        return x;
    }

    /** Distinct prime factors with exponents as {p, e} pairs flattened. */
    private static long[] factor(long n) {
        long[] out = new long[32];
        int k = 0;
        long m = n;
        for (long p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                int e = 0;
                while (m % p == 0) {
                    m /= p;
                    e++;
                }
                out[k++] = p;
                out[k++] = e;
            }
        }
        if (m > 1) {
            out[k++] = m;
            out[k++] = 1;
        }
        return java.util.Arrays.copyOf(out, k);
    }

    /** Euler phi(q). */
    public static long totient(long q) {
        check(q);
        long r = q;
        long[] f = factor(q);
        for (int i = 0; i < f.length; i += 2) {
            r = r / f[i] * (f[i] - 1);
        }
        return r;
    }

    /** Moebius mu(q). */
    public static int mobius(long q) {
        check(q);
        long[] f = factor(q);
        for (int i = 1; i < f.length; i += 2) {
            if (f[i] > 1) {
                return 0;
            }
        }
        return ((f.length / 2) & 1) == 0 ? 1 : -1;
    }

    /** Dedekind psi(q) = q * prod (1 + 1/p). */
    public static long dedekindPsi(long q) {
        check(q);
        long r = q;
        long[] f = factor(q);
        for (int i = 0; i < f.length; i += 2) {
            r = r / f[i] * (f[i] + 1);
        }
        return r;
    }

    /** Jordan totient J_k(q) = q^k * prod (1 - p^-k), exact while the result fits in a long. */
    public static long jordanTotient(int k, long q) {
        check(q);
        if (k < 1) {
            throw new IllegalArgumentException("k must be positive: " + k);
        }
        long r = 1;
        long[] f = factor(q);
        for (int i = 0; i < f.length; i += 2) {
            long pk = 1;
            for (int j = 0; j < k; j++) {
                pk = Math.multiplyExact(pk, f[i]);
            }
            long term = pk - 1;
            for (long e = 1; e < f[i + 1]; e++) {
                term = Math.multiplyExact(term, pk);
            }
            r = Math.multiplyExact(r, term);
        }
        return r;
    }

    /** Ramanujan sum c_q(n). */
    public static long ramanujanSum(long q, long n) {
        check(q);
        long d = gcd(n, q);
        long m = q / d;
        return mobius(m) * (totient(q) / totient(m));
    }

    /** Grade a claimed echo c_q(n). */
    public static Grade grade(long q, long n, long claimed) {
        return ramanujanSum(q, n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the coprime bells cancel to a whole echo. The ring is true.";
            case SLIPPED -> "Forgemaster: the echo is off. Take the gcd, then mu and phi of what is left.";
        };
    }
}
