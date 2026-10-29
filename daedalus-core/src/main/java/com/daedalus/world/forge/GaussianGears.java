// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Gaussian Gears: forge gears are cut on the Gaussian integer lattice a+bi. The smith meshes two gears by their
 * Gaussian gcd, tells prime gears from composite ones, and splits a rim length n into two squares a^2+b^2=n.
 *
 * <p>Gaussian integers are passed as (re, im) longs with |re|,|im| at most {@link #MAX_PART}; results come back as
 * two-element arrays. Sum-of-two-squares uses factorisation, Cornacchia's algorithm per prime 1 mod 4 and Gaussian
 * multiplication, all in plain long arithmetic for n up to {@link #MAX_N}.
 */
public final class GaussianGears {

    /** Quest id for the Daedalus hook. */
    public static final String QUEST_ID = "q_gaussian_gears";
    /** Largest supported absolute component. */
    public static final long MAX_PART = 1L << 30;
    /** Largest supported rim length for sum-of-two-squares. */
    public static final long MAX_N = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private GaussianGears() {
    }

    private static void checkPart(long v) {
        if (v > MAX_PART || v < -MAX_PART) {
            throw new IllegalArgumentException("component out of range: " + v);
        }
    }

    /** Norm a^2+b^2. */
    public static long norm(long a, long b) {
        checkPart(a);
        checkPart(b);
        return a * a + b * b;
    }

    /** Nearest-integer quotient (a+bi)/(c+di); divisor must be nonzero. */
    public static long[] divRound(long a, long b, long c, long d) {
        long n = norm(c, d);
        checkPart(a);
        checkPart(b);
        if (n == 0) {
            throw new ArithmeticException("division by zero gear");
        }
        long x = a * c + b * d;
        long y = b * c - a * d;
        return new long[] {Math.floorDiv(2 * x + n, 2 * n), Math.floorDiv(2 * y + n, 2 * n)};
    }

    /** True when c+di divides a+bi exactly. */
    public static boolean divides(long c, long d, long a, long b) {
        long n = norm(c, d);
        checkPart(a);
        checkPart(b);
        if (n == 0) {
            return a == 0 && b == 0;
        }
        return (a * c + b * d) % n == 0 && (b * c - a * d) % n == 0;
    }

    /** Normalise to the associate with re &gt; 0 and im &gt;= 0 (zero stays zero). */
    static long[] normalise(long a, long b) {
        long x = a;
        long y = b;
        for (int k = 0; k < 4 && !(x > 0 && y >= 0) && (x != 0 || y != 0); k++) {
            long t = x;
            x = -y;
            y = t;
        }
        return new long[] {x, y};
    }

    /** Gaussian gcd, normalised to the first quadrant. */
    public static long[] gcd(long a, long b, long c, long d) {
        checkPart(a);
        checkPart(b);
        checkPart(c);
        checkPart(d);
        long x = a;
        long y = b;
        long u = c;
        long v = d;
        while (u != 0 || v != 0) {
            long[] q = divRound(x, y, u, v);
            long rx = x - (q[0] * u - q[1] * v);
            long ry = y - (q[0] * v + q[1] * u);
            x = u;
            y = v;
            u = rx;
            v = ry;
        }
        return normalise(x, y);
    }

    static boolean isPrimeLong(long n) {
        if (n < 2) {
            return false;
        }
        if (n % 2 == 0) {
            return n == 2;
        }
        for (long f = 3; f * f <= n; f += 2) {
            if (n % f == 0) {
                return false;
            }
        }
        return true;
    }

    /** True when a+bi is a Gaussian prime. */
    public static boolean isPrime(long a, long b) {
        checkPart(a);
        checkPart(b);
        if (a == 0 || b == 0) {
            long m = Math.abs(a + b);
            return isPrimeLong(m) && (m & 3) == 3;
        }
        return isPrimeLong(a * a + b * b);
    }

    /** Number of ordered integer pairs (a,b) with a^2+b^2=n (r2). */
    public static long countRepresentations(long n) {
        check(n);
        if (n == 0) {
            return 1;
        }
        long m = n;
        while ((m & 1) == 0) {
            m >>= 1;
        }
        long r = 4;
        for (long p = 3; p * p <= m; p += 2) {
            int e = 0;
            while (m % p == 0) {
                m /= p;
                e++;
            }
            if ((p & 3) == 1) {
                r *= e + 1;
            } else if ((e & 1) == 1) {
                return 0;
            }
        }
        if (m > 1) {
            if ((m & 3) == 1) {
                r *= 2;
            } else {
                return 0;
            }
        }
        return r;
    }

    private static void check(long n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("rim length out of range: " + n);
        }
    }

    static long isqrt(long n) {
        long r = (long) Math.sqrt((double) n);
        while (r * r > n) {
            r--;
        }
        while ((r + 1) * (r + 1) <= n) {
            r++;
        }
        return r;
    }

    static long mulMod(long a, long b, long m) {
        return java.math.BigInteger.valueOf(a).multiply(java.math.BigInteger.valueOf(b))
                .mod(java.math.BigInteger.valueOf(m)).longValue();
    }

    static long powMod(long b, long e, long m) {
        long r = 1 % m;
        long x = b % m;
        long k = e;
        while (k > 0) {
            if ((k & 1) == 1) {
                r = mulMod(r, x, m);
            }
            x = mulMod(x, x, m);
            k >>= 1;
        }
        return r;
    }

    /** Cornacchia for a prime p = 1 mod 4: returns {a, b} with a^2+b^2=p, a &gt; b &gt; 0. */
    static long[] primeSquares(long p) {
        long x = 0;
        for (long z = 2; x == 0; z++) {
            long t = powMod(z, (p - 1) / 4, p);
            if (mulMod(t, t, p) == p - 1) {
                x = t;
            }
        }
        long r0 = p;
        long r1 = x;
        long root = isqrt(p);
        while (r1 > root) {
            long t = r0 % r1;
            r0 = r1;
            r1 = t;
        }
        long a = r1;
        long b = isqrt(p - a * a);
        return a >= b ? new long[] {a, b} : new long[] {b, a};
    }

    private static long[] mul(long[] z, long a, long b) {
        return new long[] {z[0] * a - z[1] * b, z[0] * b + z[1] * a};
    }

    /** Some {a, b} with a &gt;= b &gt;= 0 and a^2+b^2=n, or an empty array when n is not a sum of two squares. */
    public static long[] twoSquares(long n) {
        if (countRepresentations(n) == 0) {
            return new long[0];
        }
        if (n == 0) {
            return new long[] {0, 0};
        }
        long[] z = {1, 0};
        long m = n;
        while ((m & 1) == 0) {
            m >>= 1;
            z = mul(z, 1, 1);
        }
        for (long p = 3; p * p <= m; p += 2) {
            if (m % p != 0) {
                continue;
            }
            long[] ps = (p & 3) == 1 ? primeSquares(p) : null;
            while (m % p == 0) {
                m /= p;
                if (ps == null) {
                    m /= p;
                    z = mul(z, p, 0);
                } else {
                    z = mul(z, ps[0], ps[1]);
                }
            }
        }
        if (m > 1) {
            long[] ps = primeSquares(m);
            z = mul(z, ps[0], ps[1]);
        }
        long a = Math.abs(z[0]);
        long b = Math.abs(z[1]);
        return a >= b ? new long[] {a, b} : new long[] {b, a};
    }

    /** Grade a claimed split of rim length n into a^2+b^2. */
    public static Grade grade(long n, long a, long b) {
        check(n);
        long s = isqrt(MAX_N);
        boolean ok = Math.abs(a) <= s && Math.abs(b) <= s && a * a + b * b == n;
        return ok ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: two square gears, one true rim. The lattice meshes clean.";
            case SLIPPED -> "Forgemaster: the rim slipped. Split it over primes 1 mod 4 and pair the gears.";
        };
    }
}
