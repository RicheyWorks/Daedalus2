// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Calkin Coils: the coilsmith walks the Calkin-Wilf tree of positive ratios, where a/b has children
 * a/(a+b) and (a+b)/b, numbered breadth-first from 1/1 at index 1.
 *
 * <p>Reusable plain long API: {@link #at}, {@link #indexOf}, {@link #next}, {@link #fusc}.
 */
public final class CalkinCoils {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_calkin_coils";

    /** Deepest tree level (index bit length minus one) supported. */
    public static final int MAX_DEPTH = 62;

    /** Grade band. */
    public enum Grade { TRUE, KINKED }

    /** A positive reduced ratio. */
    public record Ratio(long num, long den) {
    }

    private CalkinCoils() {
    }

    /** Seeded coil index in [1, 2^20]. */
    public static long coil(long seed) {
        return 1 + new SplittableRandom(seed).nextInt(1 << 20);
    }

    /** Ratio at breadth-first index k (k &gt;= 1). */
    public static Ratio at(long k) {
        if (k < 1) {
            throw new IllegalArgumentException("index must be positive");
        }
        long a = 1;
        long b = 1;
        for (int bit = 62 - Long.numberOfLeadingZeros(k); bit >= 0; bit--) {
            if (((k >>> bit) & 1L) == 1L) {
                a += b;
            } else {
                b += a;
            }
        }
        return new Ratio(a, b);
    }

    /** Breadth-first index of the reduced ratio a/b. */
    public static long indexOf(long a, long b) {
        if (a < 1 || b < 1 || gcd(a, b) != 1) {
            throw new IllegalArgumentException("need a positive reduced ratio");
        }
        long[] runs = new long[130];
        boolean[] ones = new boolean[130];
        int m = 0;
        long depth = 0;
        while (a != b) {
            if (a < b) {
                long r = (b - 1) / a;
                b -= r * a;
                runs[m] = r;
                ones[m++] = false;
                depth += r;
            } else {
                long r = (a - 1) / b;
                a -= r * b;
                runs[m] = r;
                ones[m++] = true;
                depth += r;
            }
            if (depth > MAX_DEPTH) {
                throw new IllegalArgumentException("ratio too deep in the tree");
            }
        }
        long idx = 1;
        for (int i = m - 1; i >= 0; i--) {
            int r = (int) runs[i];
            idx = (idx << r) | (ones[i] ? (1L << r) - 1 : 0L);
        }
        return idx;
    }

    /** Next ratio in breadth-first order (Newman's formula). */
    public static Ratio next(long a, long b) {
        return new Ratio(b, 2 * (a / b) * b + b - a);
    }

    /** Stern's diatomic sequence: fusc(0)=0, fusc(1)=1, fusc(2n)=fusc(n), fusc(2n+1)=fusc(n)+fusc(n+1). */
    public static long fusc(long n) {
        if (n < 0) {
            throw new IllegalArgumentException("n must be non-negative");
        }
        long a = 1;
        long b = 0;
        long x = n;
        while (x > 0) {
            if ((x & 1L) == 1L) {
                b += a;
            } else {
                a += b;
            }
            x >>>= 1;
        }
        return b;
    }

    /** TRUE when the claimed ratio sits at index k. */
    public static Grade grade(long k, long num, long den) {
        return at(k).equals(new Ratio(num, den)) ? Grade.TRUE : Grade.KINKED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: right turn, left turn, and the coil lands true on its ratio.";
            case KINKED -> "Forgemaster: that coil is kinked. Walk the tree again from the root.";
        };
    }

    private static long gcd(long x, long y) {
        long p = x;
        long q = y;
        while (q != 0) {
            long t = p % q;
            p = q;
            q = t;
        }
        return p;
    }
}
