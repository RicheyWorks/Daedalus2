// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Proth Plates: a plate N = k x 2^n + 1 with odd k and 0 &lt; k &lt; 2^n is a Proth plate (3, 5, 9, 13, 17, 25, ...).
 * By Proth's theorem it is prime exactly when some a has a^((N-1)/2) = -1 (mod N); a quadratic non-residue
 * (Jacobi symbol -1) is such a witness whenever N is prime.
 *
 * <p>Reusable plain long API for 1 &lt;= N &lt;= {@link #MAX_N}: {@link #split}, {@link #isProth}, {@link #jacobi},
 * {@link #witness}, {@link #isProthPrime}, {@link #countProth}.
 */
public final class ProthPlates {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_proth_plates";
    /** Largest supported plate. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;
    /** Largest witness searched. */
    public static final int WITNESS_LIMIT = 10_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private ProthPlates() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("plate out of range: " + n);
        }
    }

    /** {k, n} with N - 1 = k x 2^n and k odd; N must be odd and at least 3. */
    public static long[] split(long big) {
        check(big);
        if (big < 3 || (big & 1) == 0) {
            throw new IllegalArgumentException("plate must be odd and at least 3: " + big);
        }
        long m = big - 1;
        int n = Long.numberOfTrailingZeros(m);
        return new long[] {m >> n, n};
    }

    /** True when N is a Proth number. */
    public static boolean isProth(long big) {
        check(big);
        if (big < 3 || (big & 1) == 0) {
            return false;
        }
        long[] kn = split(big);
        return (kn[0] >> kn[1]) == 0;
    }

    private static long mulMod(long a, long b, long m) {
        long r = 0;
        long x = a % m;
        long y = b;
        while (y > 0) {
            if ((y & 1) != 0) {
                r += x;
                if (r >= m) {
                    r -= m;
                }
            }
            x += x;
            if (x >= m) {
                x -= m;
            }
            y >>= 1;
        }
        return r;
    }

    private static long powMod(long a, long e, long m) {
        long r = 1 % m;
        long b = a % m;
        long x = e;
        while (x > 0) {
            if ((x & 1) != 0) {
                r = mulMod(r, b, m);
            }
            b = mulMod(b, b, m);
            x >>= 1;
        }
        return r;
    }

    /** Jacobi symbol (a / m) for odd positive m. */
    public static int jacobi(long a, long m) {
        if (m < 1 || (m & 1) == 0) {
            throw new IllegalArgumentException("modulus must be odd and positive: " + m);
        }
        long x = Math.floorMod(a, m);
        long y = m;
        int t = 1;
        while (x != 0) {
            while ((x & 1) == 0) {
                x >>= 1;
                long r = y & 7;
                if (r == 3 || r == 5) {
                    t = -t;
                }
            }
            long s = x;
            x = y;
            y = s;
            if ((x & 3) == 3 && (y & 3) == 3) {
                t = -t;
            }
            x %= y;
        }
        return y == 1 ? t : 0;
    }

    /** Smallest a &gt;= 2 with Jacobi (a / N) = -1, or 0 when none up to {@link #WITNESS_LIMIT}. */
    public static int witness(long big) {
        check(big);
        if ((big & 1) == 0) {
            throw new IllegalArgumentException("plate must be odd: " + big);
        }
        for (int a = 2; a <= WITNESS_LIMIT && a < big; a++) {
            if (jacobi(a, big) == -1) {
                return a;
            }
        }
        return 0;
    }

    /** True when N is a prime Proth plate, decided by Proth's theorem. */
    public static boolean isProthPrime(long big) {
        if (!isProth(big)) {
            return false;
        }
        for (int a = 2; a <= WITNESS_LIMIT && a < big; a++) {
            int j = jacobi(a, big);
            if (j == 0) {
                return false;
            }
            if (j == -1) {
                return powMod(a, (big - 1) / 2, big) == big - 1;
            }
        }
        return PrimorialPyres.isPrime(big);
    }

    /** Number of Proth plates in 1..x. */
    public static long countProth(long x) {
        if (x < 0 || x > MAX_N) {
            throw new IllegalArgumentException("bound out of range: " + x);
        }
        long c = 0;
        for (int n = 1; n < 62 && (1L << n) < x; n++) {
            long m = Math.min((1L << n) - 1, (x - 1) >> n);
            c += (m + 1) / 2;
        }
        return c;
    }

    /** Grade a claim that N is (or is not) a prime Proth plate. */
    public static Grade grade(long big, boolean claimedPrime) {
        return isProthPrime(big) == claimedPrime ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the plate rang true. One witness is all Proth asks.";
            case SLIPPED -> "Forgemaster: the plate slipped. Strike it with a non-residue and listen again.";
        };
    }
}
