// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Map;

/**
 * G310 The Square Hatches: the shipwright asks whether a deck area n can be laid as two square
 * hatches, n = a^2 + b^2. Fermat: yes exactly when every prime 3 mod 4 divides n an even number
 * of times (prime lots from {@link CrateManifest}). Counts the signed ordered ways r2(n), finds one
 * split by Cornacchia's descent for each prime 1 mod 4 composed with the Brahmagupta identity, and
 * lays any n as four square hatches (Lagrange). Areas are below {@link LanternHandshake#MAX_MOD}.
 */
public final class SquareHatches {

    public static final String QUEST_ID = "q_square_hatches";

    private SquareHatches() { }

    private static void check(long n) {
        if (n < 0 || n >= LanternHandshake.MAX_MOD) {
            throw new IllegalArgumentException("area out of range: " + n);
        }
    }

    public static boolean isTwoSquares(long n) {
        check(n);
        if (n == 0) {
            return true;
        }
        for (Map.Entry<Long, Integer> e : CrateManifest.lots(n).entrySet()) {
            if (e.getKey() % 4 == 3 && e.getValue() % 2 != 0) {
                return false;
            }
        }
        return true;
    }

    /** Signed ordered pairs (a, b) with a^2 + b^2 = n. */
    public static long r2(long n) {
        check(n);
        if (n == 0) {
            return 1;
        }
        long ways = 4;
        for (Map.Entry<Long, Integer> e : CrateManifest.lots(n).entrySet()) {
            long p = e.getKey();
            if (p % 4 == 3 && e.getValue() % 2 != 0) {
                return 0;
            }
            if (p % 4 == 1) {
                ways *= e.getValue() + 1;
            }
        }
        return ways;
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

    /** {x, y} with x^2 + y^2 = p for p = 2 or a prime 1 mod 4. */
    static long[] primeSplit(long p) {
        if (p == 2) {
            return new long[] {1, 1};
        }
        long c = 2;
        while (LanternHandshake.powMod(c, (p - 1) / 2, p) != p - 1) {
            c++;
        }
        long x = LanternHandshake.powMod(c, (p - 1) / 4, p);
        long a = p;
        long b = x;
        long lim = isqrt(p);
        while (b > lim) {
            long t = a % b;
            a = b;
            b = t;
        }
        long y = isqrt(p - b * b);
        return new long[] {b, y};
    }

    /** One split {a, b} with a <= b and a^2 + b^2 = n, or an empty array when none exists. */
    public static long[] split(long n) {
        if (!isTwoSquares(n)) {
            return new long[0];
        }
        if (n == 0) {
            return new long[] {0, 0};
        }
        long a = 1;
        long b = 0;
        for (Map.Entry<Long, Integer> e : CrateManifest.lots(n).entrySet()) {
            long p = e.getKey();
            int k = e.getValue();
            if (p % 4 == 3) {
                for (int i = 0; i < k / 2; i++) {
                    a *= p;
                    b *= p;
                }
            } else {
                long[] xy = primeSplit(p);
                for (int i = 0; i < k; i++) {
                    long na = Math.abs(a * xy[0] - b * xy[1]);
                    long nb = a * xy[1] + b * xy[0];
                    a = na;
                    b = nb;
                }
            }
        }
        return new long[] {Math.min(a, b), Math.max(a, b)};
    }

    /** Four squares {a, b, c, d}, ascending, summing to n (always possible). */
    public static long[] fourSquares(long n) {
        check(n);
        for (long a = isqrt(n); a >= 0; a--) {
            long r1 = n - a * a;
            for (long b = Math.min(a, isqrt(r1)); b >= 0; b--) {
                long[] two = split(r1 - b * b);
                if (two.length == 2) {
                    long[] out = {two[0], two[1], b, a};
                    java.util.Arrays.sort(out);
                    return out;
                }
            }
        }
        throw new IllegalStateException("Lagrange failed for " + n);
    }

    /** Quest q_square_hatches: do the two hatch sides cover the deck area exactly? */
    public static boolean quest(long n, long a, long b) {
        check(n);
        if (a < 0 || b < 0 || a > 60_000 || b > 60_000) {
            return false;
        }
        return a * a + b * b == n;
    }
}